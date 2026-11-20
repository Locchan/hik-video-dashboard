"""DVR config (STREAMING_DVR_*) + Hikvision ISAPI channel discovery."""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
)

# Ids are single path segments (no underscores) so CH_Y_NAME / HTTP_ADDR cannot be eaten as NAME.
# STREAMING_DVR_{id}_NAME|HTTP_ADDR|RTSP_ADDR|USERNAME|PASSWORD
DVR_KEY_RE = re.compile(
    r"^STREAMING_DVR_([^_]+)_(NAME|HTTP_ADDR|RTSP_ADDR|USERNAME|PASSWORD)$"
)
# STREAMING_DVR_{id}_CH_{channel}_NAME
CH_NAME_RE = re.compile(r"^STREAMING_DVR_([^_]+)_CH_([^_]+)_NAME$")

ISAPI_TIMEOUT_S = 3.0
ISAPI_SEARCH_TIMEOUT_S = 15.0
DEFAULT_HTTP_PORT = 80
DEFAULT_RTSP_PORT = 554
_ISAPI_DEBUG_BODY_LIMIT = 16384
# Hikvision playback window when only start is given (NVR local clock, Z suffix).
DEFAULT_PLAYBACK_WINDOW = timedelta(hours=24)
# Archive bounds for datetime-local min/max (ignore holes inside the span).
DEFAULT_RECORDING_LOOKBACK_DAYS = 365
RECORDING_SEARCH_PAGE_SIZE = 100
RECORDING_SEARCH_MAX_PAGES = 40
_START_TZ_SUFFIX = re.compile(r"(Z|[+-]\d{2}:?\d{2})$", re.IGNORECASE)


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _isapi_debug_body(body: bytes, *, limit: int = _ISAPI_DEBUG_BODY_LIMIT) -> str:
    text = (body or b"").decode("utf-8", errors="replace")
    if len(text) > limit:
        return f"{text[:limit]}\n... truncated ({len(text)} chars total)"
    return text


def parse_streaming_dvr_config(entries: list[dict]) -> dict[str, dict]:
    """Parse STREAMING_DVR_* rows → id → {name, http_addr, rtsp_addr, username, password, channel_names}.

    HTTP_ADDR is used for ISAPI; RTSP_ADDR for live streams. Reads the full config table
    (typically root-owned). Streaming endpoints enforce auth + FEAT_STREAMING; secrets
    are never returned to clients.
    """
    dvrs: dict[str, dict] = {}

    def bucket(dvr_id: str) -> dict:
        return dvrs.setdefault(
            dvr_id,
            {
                "id": dvr_id,
                "name": None,
                "http_addr": None,
                "rtsp_addr": None,
                "username": None,
                "password": None,
                "channel_names": {},
            },
        )

    for entry in entries:
        key = str(entry.get("name") or "").strip()
        value = str(entry.get("value") or "").strip()
        cm = CH_NAME_RE.match(key)
        if cm:
            dvr_id, ch_id = cm.group(1), cm.group(2)
            if value:
                bucket(dvr_id)["channel_names"][ch_id] = value
            continue
        m = DVR_KEY_RE.match(key)
        if m:
            dvr_id, field = m.group(1), m.group(2)
            b = bucket(dvr_id)
            if field == "NAME":
                b["name"] = value or None
            elif field == "HTTP_ADDR":
                b["http_addr"] = value or None
            elif field == "RTSP_ADDR":
                b["rtsp_addr"] = value or None
            elif field == "USERNAME":
                b["username"] = value or None
            elif field == "PASSWORD":
                b["password"] = value  # may be empty string

    # Need both endpoints to register a usable DVR.
    return {
        did: d
        for did, d in dvrs.items()
        if d.get("http_addr") and d.get("rtsp_addr")
    }


def _http_base(addr: str) -> str:
    """Return HTTP(S) base URL without trailing slash (for ISAPI)."""
    raw = (addr or "").strip()
    if not raw:
        raise ValueError("empty DVR HTTP address")
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlsplit(raw)
    host = parsed.hostname
    if not host:
        raise ValueError(f"invalid DVR HTTP address: {addr!r}")
    port = parsed.port or DEFAULT_HTTP_PORT
    scheme = parsed.scheme or "http"
    return f"{scheme}://{host}:{port}"


def _rtsp_host_port(
    addr: str, *, default_port: int = DEFAULT_RTSP_PORT
) -> tuple[str, int]:
    """Return (host, port) from an RTSP address string."""
    raw = (addr or "").strip()
    if not raw:
        raise ValueError("empty DVR RTSP address")
    if "://" not in raw:
        raw = f"rtsp://{raw}"
    parsed = urlsplit(raw)
    host = parsed.hostname
    if not host:
        raise ValueError(f"invalid DVR RTSP address: {addr!r}")
    return host, parsed.port or default_port


def _isapi_request(
    addr: str,
    username: str,
    password: str,
    path: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    content_type: str | None = None,
    timeout_s: float = ISAPI_TIMEOUT_S,
    logger=None,
) -> bytes:
    """Digest-auth ISAPI call → response body bytes. path is absolute on the device."""
    base = _http_base(addr)
    url = f"{base}{path}"
    pwd_mgr = HTTPPasswordMgrWithDefaultRealm()
    pwd_mgr.add_password(None, base, username or "", password or "")
    opener = build_opener(HTTPDigestAuthHandler(pwd_mgr))
    headers = {"Accept": "application/xml"}
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(url, data=data, method=method, headers=headers)
    if logger is not None:
        # URL has no credentials (Digest is via opener); safe to log at DEBUG.
        logger.debug("ISAPI request %s %s", method, url)
    try:
        with opener.open(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            body = resp.read()
            if logger is not None:
                logger.debug(
                    "ISAPI response %s %s -> %s (%s bytes)\n%s",
                    method,
                    url,
                    status,
                    len(body),
                    _isapi_debug_body(body),
                )
            return body
    except HTTPError as e:
        err_body = b""
        try:
            err_body = e.read() or b""
        except Exception:
            pass
        if logger is not None:
            logger.debug(
                "ISAPI response %s %s -> %s (%s bytes)\n%s",
                method,
                url,
                e.code,
                len(err_body),
                _isapi_debug_body(err_body),
            )
        raise RuntimeError(f"ISAPI HTTP {e.code}") from e
    except URLError as e:
        if logger is not None:
            logger.debug(
                "ISAPI request %s %s failed: unreachable (%s)",
                method,
                url,
                e.reason,
            )
        raise RuntimeError(f"ISAPI unreachable: {e.reason}") from e
    except TimeoutError as e:
        if logger is not None:
            logger.debug("ISAPI request %s %s failed: timeout", method, url)
        raise RuntimeError("ISAPI timeout") from e


def fetch_channel_ids(
    addr: str,
    username: str,
    password: str,
    *,
    timeout_s: float = ISAPI_TIMEOUT_S,
    logger=None,
) -> list[str]:
    """GET /ISAPI/Streaming/channels (Digest) → list of channel id strings."""
    body = _isapi_request(
        addr,
        username,
        password,
        "/ISAPI/Streaming/channels",
        timeout_s=timeout_s,
        logger=logger,
    )
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        if logger is not None:
            logger.debug("ISAPI Streaming/channels: invalid XML")
        raise RuntimeError("ISAPI returned invalid XML") from e

    ids: list[str] = []
    seen: set[str] = set()
    for el in root.iter():
        if _local(el.tag) != "StreamingChannel":
            continue
        for child in el:
            if _local(child.tag) != "id":
                continue
            text = (child.text or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ids.append(text)
            break
    ids.sort(key=lambda s: int(s) if s.isdigit() else s)
    return ids


def _hik_cm_stamp(moment: datetime) -> str:
    """ContentMgmt search stamp as NVR-local wall time (no Z → device local TZ)."""
    naive = moment.replace(tzinfo=None) if moment.tzinfo is not None else moment
    return naive.strftime("%Y-%m-%dT%H:%M:%S")


def _parse_cm_stamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip().replace(" ", "T", 1)
    tz = _START_TZ_SUFFIX.search(text)
    if tz:
        text = text[: tz.start()]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _datetime_local_value(moment: datetime) -> str:
    naive = moment.replace(tzinfo=None) if moment.tzinfo is not None else moment
    return naive.strftime("%Y-%m-%dT%H:%M")


def _build_cm_search_xml(
    track_id: str,
    start: datetime,
    end: datetime,
    *,
    offset: int,
    max_results: int,
) -> bytes:
    search_id = str(uuid.uuid4()).upper()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<CMSearchDescription>"
        f"<searchID>{search_id}</searchID>"
        f"<trackIDList><trackID>{track_id}</trackID></trackIDList>"
        "<timeSpanList><timeSpan>"
        f"<startTime>{_hik_cm_stamp(start)}</startTime>"
        f"<endTime>{_hik_cm_stamp(end)}</endTime>"
        "</timeSpan></timeSpanList>"
        f"<maxResults>{int(max_results)}</maxResults>"
        f"<searchResultPostion>{int(offset)}</searchResultPostion>"
        "</CMSearchDescription>"
    )
    return xml.encode("utf-8")


def _parse_cm_search_result(body: bytes) -> tuple[str, list[tuple[datetime, datetime]]]:
    """Return (responseStatusStrg, [(start, end), ...])."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise RuntimeError("ISAPI returned invalid XML") from e

    status = "OK"
    for el in root.iter():
        if _local(el.tag) == "responseStatusStrg":
            status = (el.text or "").strip().upper() or "OK"
            break

    spans: list[tuple[datetime, datetime]] = []
    for el in root.iter():
        if _local(el.tag) != "searchMatchItem":
            continue
        start_raw = end_raw = None
        for child in el.iter():
            tag = _local(child.tag)
            if tag == "startTime" and start_raw is None:
                start_raw = child.text
            elif tag == "endTime" and end_raw is None:
                end_raw = child.text
        start = _parse_cm_stamp(start_raw)
        end = _parse_cm_stamp(end_raw)
        if start is None:
            continue
        if end is None or end < start:
            end = start
        spans.append((start, end))
    return status, spans


def _search_recording_spans(
    addr: str,
    username: str,
    password: str,
    track_id: str,
    start: datetime,
    end: datetime,
    *,
    timeout_s: float = ISAPI_SEARCH_TIMEOUT_S,
    page_size: int = RECORDING_SEARCH_PAGE_SIZE,
    max_pages: int = RECORDING_SEARCH_MAX_PAGES,
    logger=None,
) -> list[tuple[datetime, datetime]]:
    """Paginated ContentMgmt/search → list of (start, end) spans."""
    track = str(track_id or "").strip()
    if not track:
        raise ValueError("empty track id")
    if end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    if end <= start:
        return []

    spans_out: list[tuple[datetime, datetime]] = []
    offset = 0
    for _ in range(max(1, int(max_pages))):
        body = _isapi_request(
            addr,
            username,
            password,
            "/ISAPI/ContentMgmt/search",
            method="POST",
            data=_build_cm_search_xml(
                track, start, end, offset=offset, max_results=page_size
            ),
            content_type="application/xml",
            timeout_s=timeout_s,
            logger=logger,
        )
        status, spans = _parse_cm_search_result(body)
        if status == "NO MATCHES" or not spans:
            break
        spans_out.extend(spans)
        offset += len(spans)
        if status != "MORE" or len(spans) < page_size:
            break
    return spans_out


def fetch_recording_bounds(
    addr: str,
    username: str,
    password: str,
    track_id: str,
    *,
    lookback_days: int = DEFAULT_RECORDING_LOOKBACK_DAYS,
    timeout_s: float = ISAPI_SEARCH_TIMEOUT_S,
    page_size: int = RECORDING_SEARCH_PAGE_SIZE,
    max_pages: int = RECORDING_SEARCH_MAX_PAGES,
    now: datetime | None = None,
    logger=None,
) -> dict[str, str] | None:
    """POST /ISAPI/ContentMgmt/search → {min, max} datetime-local strings, or None.

    Coarse archive extent only — holes inside are common; use
    ``find_recording_cover`` before playback.
    """
    end = (now or datetime.now()).replace(microsecond=0)
    if end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    start = end - timedelta(days=max(1, int(lookback_days)))
    spans = _search_recording_spans(
        addr,
        username,
        password,
        track_id,
        start,
        end,
        timeout_s=timeout_s,
        page_size=page_size,
        max_pages=max_pages,
        logger=logger,
    )
    if not spans:
        return None
    earliest = min(s[0] for s in spans)
    latest = max(s[1] for s in spans)
    return {
        "min": _datetime_local_value(earliest),
        "max": _datetime_local_value(latest),
        "days": _days_from_spans(spans),
    }


def _days_from_spans(spans: list[tuple[datetime, datetime]]) -> list[str]:
    """Calendar days (YYYY-MM-DD) that intersect any recorded span."""
    days: set[str] = set()
    for span_start, span_end in spans:
        day = span_start.date()
        last = span_end.date()
        if last < day:
            last = day
        while day <= last:
            days.add(day.isoformat())
            day = day + timedelta(days=1)
    return sorted(days)


def find_recording_cover(
    addr: str,
    username: str,
    password: str,
    track_id: str,
    at: datetime,
    *,
    window_before: timedelta = timedelta(hours=12),
    window_after: timedelta = timedelta(hours=12),
    timeout_s: float = ISAPI_SEARCH_TIMEOUT_S,
    logger=None,
) -> datetime | None:
    """Return a playable start if a recorded span covers ``at``, else None.

    ContentMgmt min/max spans often leave holes; RTSP playback only works inside
    real segments. When ``at`` falls inside a segment, returns ``at`` (NVR-local).
    """
    moment = at.replace(tzinfo=None) if at.tzinfo is not None else at
    spans = _search_recording_spans(
        addr,
        username,
        password,
        track_id,
        moment - window_before,
        moment + window_after,
        timeout_s=timeout_s,
        page_size=RECORDING_SEARCH_PAGE_SIZE,
        max_pages=min(10, RECORDING_SEARCH_MAX_PAGES),
        logger=logger,
    )
    for span_start, span_end in spans:
        if span_start <= moment <= span_end:
            return moment
    return None


def _hik_rtsp_stamp(moment: datetime) -> str:
    """Format for Hikvision starttime/endtime (NVR local wall time, trailing Z)."""
    naive = moment.replace(tzinfo=None) if moment.tzinfo is not None else moment
    return naive.strftime("%Y%m%dT%H%M%SZ")


def parse_playback_start(raw: str | None) -> datetime | None:
    """Parse ?start= as NVR-local naive datetime (from datetime-local / ISO without Z)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # datetime-local: 2024-01-02T15:04 or with seconds; allow space separator.
    text = text.replace(" ", "T", 1)
    tz = _START_TZ_SUFFIX.search(text)
    if tz:
        text = text[: tz.start()]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"invalid start time: {raw!r}")


def build_rtsp_url(
    addr: str,
    username: str,
    password: str,
    channel: str,
    *,
    default_rtsp_port: int = DEFAULT_RTSP_PORT,
    start: datetime | None = None,
    end: datetime | None = None,
) -> str:
    """Live Channels URL, or tracks playback URL when ``start`` is set."""
    host, port = _rtsp_host_port(addr, default_port=default_rtsp_port)
    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    ch = quote(str(channel).strip(), safe="")
    auth = f"{user}:{pwd}@" if (username or password) else ""
    if start is None:
        return f"rtsp://{auth}{host}:{port}/Streaming/Channels/{ch}"
    if end is None:
        end = start + DEFAULT_PLAYBACK_WINDOW
    if end <= start:
        raise ValueError("playback end must be after start")
    st = _hik_rtsp_stamp(start)
    et = _hik_rtsp_stamp(end)
    return (
        f"rtsp://{auth}{host}:{port}/Streaming/tracks/{ch}/"
        f"?starttime={st}&endtime={et}"
    )


def list_dvrs_with_channels(
    entries: list[dict],
    *,
    timeout_s: float = ISAPI_TIMEOUT_S,
    fetch_fn: Callable[..., list[str]] | None = None,
    logger=None,
) -> dict[str, dict]:
    """Return public payload: { DVR_{id}: { NAME, CHANNELS: { id: { NAME } } } }."""
    dvrs = parse_streaming_dvr_config(entries)
    fetch = fetch_fn or (
        lambda a, u, p: fetch_channel_ids(
            a, u, p, timeout_s=timeout_s, logger=logger
        )
    )
    out: dict[str, dict] = {}

    def one(dvr_id: str, dvr: dict) -> tuple[str, dict]:
        display_name = dvr.get("name") or f"DVR_{dvr_id}"
        channels: dict[str, dict] = {}
        try:
            ch_ids = fetch(
                dvr["http_addr"],
                dvr.get("username") or "",
                dvr.get("password") or "",
            )
        except Exception as e:
            if logger is not None:
                logger.debug(
                    "ISAPI channel list failed for DVR_%s: %s", dvr_id, e
                )
            ch_ids = []
        for ch in ch_ids:
            ch_name = dvr.get("channel_names", {}).get(ch) or ch
            channels[ch] = {"NAME": ch_name}
        return f"DVR_{dvr_id}", {"NAME": display_name, "CHANNELS": channels}

    if not dvrs:
        return out

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(dvrs)))) as pool:
        futures = {
            pool.submit(one, did, dvr): did for did, dvr in dvrs.items()
        }
        for fut in as_completed(futures):
            key, payload = fut.result()
            out[key] = payload
    # Stable key order
    return {k: out[k] for k in sorted(out.keys())}


def resolve_dvr(entries: list[dict], dvr_id: str) -> dict | None:
    """Return parsed DVR dict for id X (from STREAMING_DVR_X_*), or None."""
    dvr_id = (dvr_id or "").strip()
    if dvr_id.upper().startswith("DVR_"):
        dvr_id = dvr_id[4:]
    return parse_streaming_dvr_config(entries).get(dvr_id)


def query_stream_params(
    path: str,
) -> tuple[str | None, str | None, str | None]:
    """Extract (dvr, channel, start) from ?dvr=&channel=&start= on a request path."""
    parsed = urlsplit(path or "")
    q = parse_qs(parsed.query, keep_blank_values=True)

    def first(key: str) -> str | None:
        values = q.get(key) or []
        if not values:
            return None
        raw = str(values[0]).strip()
        return raw or None

    dvr = first("dvr")
    channel = first("channel")
    start = first("start")
    if dvr and dvr.upper().startswith("DVR_"):
        dvr = dvr[4:]
    return dvr, channel, start
