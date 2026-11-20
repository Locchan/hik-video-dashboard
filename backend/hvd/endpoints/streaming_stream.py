"""WebSocket GET /streaming/stream?dvr=X&channel=Y — MPEG-TS from DVR RTSP."""

from __future__ import annotations

from urllib.parse import urlsplit

from purest import auth, feat_req, get_config, websocket
from purest.auth import PUR_CAP_BASIC_USER, auth_username

from hvd import state
from hvd.features import FEAT_STREAMING
from hvd.streaming.dvr import build_rtsp_url, query_stream_params, resolve_dvr
from hvd.streaming.ffmpeg_stream import stream_rtsp_mpegts

ENDP_PATH = "/streaming/stream"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "WebSocket: live MPEG-TS for ?dvr=<id>&channel=<id> (ffmpeg -c copy from RTSP).",
}


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_STREAMING)
@websocket
def impl_GET(headers, ws):
    cfg = get_config()
    logger = cfg.logger
    username = auth_username(headers)
    path = getattr(ws.request, "path", "") or ""
    dvr_id, channel = query_stream_params(path)
    if not dvr_id or not channel:
        try:
            ws.send({"error": "missing dvr or channel query parameter"})
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

    try:
        rtsp = build_rtsp_url(
            dvr["rtsp_addr"],
            dvr.get("username") or "",
            dvr.get("password") or "",
            channel,
        )
    except ValueError as e:
        try:
            ws.send({"error": str(e)})
        except Exception:
            pass
        return

    safe = urlsplit(rtsp)
    logger.info(
        "streaming dvr=%s channel=%s user=%s host=%s",
        dvr_id,
        channel,
        username,
        safe.hostname or "?",
    )
    stream_rtsp_mpegts(ws, rtsp, logger=logger)
