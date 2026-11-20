"""GET /streaming/recordings?dvr=&channel=[&at=] — archive bounds / cover check."""

from __future__ import annotations

from purest import api_endp, auth, feat_req, get_config
from purest.auth import PUR_CAP_BASIC_USER

from hvd import state
from hvd.features import FEAT_STREAMING
from hvd.streaming.dvr import (
    fetch_recording_bounds,
    find_recording_cover,
    parse_playback_start,
    resolve_dvr,
)

ENDP_PATH = "/streaming/recordings"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": (
        "Recording index via ISAPI ContentMgmt/search. Query: dvr, channel. "
        "Without at: {min, max, days[]} — archive extent and calendar days that "
        "intersect any ContentMgmt segment (holes omitted from days). "
        "With at=YYYY-MM-DDTHH:MM: {available, start} if a segment covers that time."
    ),
}


def _query_arg(query, key: str) -> str | None:
    if not query:
        return None
    value = query.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    raw = str(value).strip()
    return raw or None


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_STREAMING)
@api_endp
def impl_GET(headers, query=None):
    _ = headers
    cfg = get_config()
    dvr_id = _query_arg(query, "dvr")
    channel = _query_arg(query, "channel")
    at_raw = _query_arg(query, "at")
    if dvr_id and dvr_id.upper().startswith("DVR_"):
        dvr_id = dvr_id[4:]
    if not dvr_id or not channel:
        return (
            400,
            {
                "error": "dvr and channel are required",
                "min": None,
                "max": None,
                "available": False,
                "start": None,
            },
        )

    store = state.app_db.config_store
    dvr = resolve_dvr(store.list_all(), dvr_id)
    if dvr is None:
        return (
            404,
            {
                "error": "unknown DVR",
                "min": None,
                "max": None,
                "available": False,
                "start": None,
            },
        )

    http = dvr["http_addr"]
    user = dvr.get("username") or ""
    password = dvr.get("password") or ""

    if at_raw is not None:
        try:
            at = parse_playback_start(at_raw)
        except ValueError as e:
            return (400, {"error": str(e), "available": False, "start": None})
        if at is None:
            return (400, {"error": "at is required", "available": False, "start": None})
        try:
            cover = find_recording_cover(
                http, user, password, channel, at, logger=cfg.logger
            )
        except Exception as e:
            cfg.logger.debug(
                "recording cover failed dvr=%s channel=%s: %s", dvr_id, channel, e
            )
            return (
                502,
                {
                    "error": "recording search failed",
                    "available": False,
                    "start": None,
                },
            )
        if cover is None:
            return {"available": False, "start": None}
        return {
            "available": True,
            "start": cover.strftime("%Y-%m-%dT%H:%M"),
        }

    try:
        bounds = fetch_recording_bounds(
            http, user, password, channel, logger=cfg.logger
        )
    except Exception as e:
        cfg.logger.debug(
            "recording bounds failed dvr=%s channel=%s: %s", dvr_id, channel, e
        )
        return (502, {"error": "recording search failed", "min": None, "max": None})

    if bounds is None:
        return {"min": None, "max": None}
    return bounds
