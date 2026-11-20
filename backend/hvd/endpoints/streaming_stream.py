"""WebSocket GET /streaming/stream?dvr=X&channel=Y[&start=] — MPEG-TS from DVR RTSP."""

from __future__ import annotations

from urllib.parse import urlsplit

from purest import auth, feat_req, get_config, websocket
from purest.auth import PUR_CAP_BASIC_USER, auth_username

from hvd import state
from hvd.features import FEAT_STREAMING
from hvd.streaming.dvr import (
    build_rtsp_url,
    find_recording_cover,
    parse_playback_start,
    query_stream_params,
    resolve_dvr,
)
from hvd.streaming.ffmpeg_stream import stream_rtsp_mpegts

ENDP_PATH = "/streaming/stream"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": (
        "WebSocket: MPEG-TS for ?dvr=&channel= (live Channels) or "
        "&start=YYYY-MM-DDTHH:MM (playback via Streaming/tracks)."
    ),
}


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_STREAMING)
@websocket
def impl_GET(headers, ws):
    cfg = get_config()
    logger = cfg.logger
    username = auth_username(headers)
    path = getattr(ws.request, "path", "") or ""
    dvr_id, channel, start_raw = query_stream_params(path)
    if not dvr_id or not channel:
        try:
            ws.send({"error": "missing dvr or channel query parameter"})
        except Exception:
            pass
        return

    try:
        start = parse_playback_start(start_raw)
    except ValueError as e:
        try:
            ws.send({"error": str(e), "code": "bad_start"})
        except Exception:
            pass
        return

    store = state.app_db.config_store
    dvr = resolve_dvr(store.list_all(), dvr_id)
    if dvr is None:
        try:
            ws.send({"error": f"unknown dvr '{dvr_id}'"})
        except Exception:
            pass
        return

    if start is not None:
        # min/max from ContentMgmt spans holes; confirm a real segment covers start.
        try:
            cover = find_recording_cover(
                dvr["http_addr"],
                dvr.get("username") or "",
                dvr.get("password") or "",
                channel,
                start,
                logger=logger,
            )
        except Exception as e:
            logger.debug(
                "recording cover check failed dvr=%s channel=%s: %s",
                dvr_id,
                channel,
                e,
            )
            cover = None
        if cover is None:
            try:
                ws.send(
                    {
                        "error": "No recording at this time",
                        "code": "no_recording",
                    }
                )
            except Exception:
                pass
            return
        start = cover

    try:
        rtsp = build_rtsp_url(
            dvr["rtsp_addr"],
            dvr.get("username") or "",
            dvr.get("password") or "",
            channel,
            start=start,
        )
    except ValueError as e:
        try:
            ws.send({"error": str(e)})
        except Exception:
            pass
        return

    safe = urlsplit(rtsp)
    logger.info(
        "streaming dvr=%s channel=%s start=%s user=%s host=%s",
        dvr_id,
        channel,
        start.isoformat(sep="T", timespec="seconds") if start else "live",
        username,
        safe.hostname or "?",
    )
    stream_rtsp_mpegts(ws, rtsp, logger=logger)
