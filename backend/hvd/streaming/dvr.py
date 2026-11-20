"""DVR config (STREAMING_DVR_*) + Hikvision ISAPI channel discovery."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
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
DEFAULT_HTTP_PORT = 80
DEFAULT_RTSP_PORT = 554
_ISAPI_DEBUG_BODY_LIMIT = 16384


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


def fetch_channel_ids(
    addr: str,
    username: str,
    password: str,
    *,
    timeout_s: float = ISAPI_TIMEOUT_S,
    logger=None,
) -> list[str]:
    """GET /ISAPI/Streaming/channels (Digest) → list of channel id strings."""
    base = _http_base(addr)
    url = f"{base}/ISAPI/Streaming/channels"
    pwd_mgr = HTTPPasswordMgrWithDefaultRealm()
    pwd_mgr.add_password(None, base, username or "", password or "")
    opener = build_opener(HTTPDigestAuthHandler(pwd_mgr))
    req = Request(url, method="GET", headers={"Accept": "application/xml"})
    if logger is not None:
        # URL has no credentials (Digest is via opener); safe to log at DEBUG.
        logger.debug("ISAPI request GET %s", url)
    try:
        with opener.open(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            body = resp.read()
            if logger is not None:
                logger.debug(
                    "ISAPI response GET %s -> %s (%s bytes)\n%s",
                    url,
                    status,
                    len(body),
                    _isapi_debug_body(body),
                )
    except HTTPError as e:
        err_body = b""
        try:
            err_body = e.read() or b""
        except Exception:
            pass
        if logger is not None:
            logger.debug(
                "ISAPI response GET %s -> %s (%s bytes)\n%s",
                url,
                e.code,
                len(err_body),
                _isapi_debug_body(err_body),
            )
        raise RuntimeError(f"ISAPI HTTP {e.code}") from e
    except URLError as e:
        if logger is not None:
            logger.debug("ISAPI request GET %s failed: unreachable (%s)", url, e.reason)
        raise RuntimeError(f"ISAPI unreachable: {e.reason}") from e
    except TimeoutError as e:
        if logger is not None:
            logger.debug("ISAPI request GET %s failed: timeout", url)
        raise RuntimeError("ISAPI timeout") from e

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        if logger is not None:
            logger.debug("ISAPI response GET %s: invalid XML", url)
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


def build_rtsp_url(
    addr: str,
    username: str,
    password: str,
    channel: str,
    *,
    default_rtsp_port: int = DEFAULT_RTSP_PORT,
) -> str:
    host, port = _rtsp_host_port(addr, default_port=default_rtsp_port)
    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    ch = quote(str(channel).strip(), safe="")
    auth = f"{user}:{pwd}@" if (username or password) else ""
    return f"rtsp://{auth}{host}:{port}/Streaming/Channels/{ch}"


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


def query_stream_params(path: str) -> tuple[str | None, str | None]:
    """Extract (dvr, channel) from ?dvr=&channel= on a request path."""
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
    if dvr and dvr.upper().startswith("DVR_"):
        dvr = dvr[4:]
    return dvr, channel
