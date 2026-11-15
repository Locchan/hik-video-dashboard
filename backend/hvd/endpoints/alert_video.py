"""GET /alert_video?id= — stream alert clip as video/mp4."""

from __future__ import annotations

from pathlib import Path

from purest import api_endp, auth, feat_req
from purest.auth import PUR_CAP_BASIC_USER

from hvd import state
from hvd.features import FEAT_ALERT_VIEW
from hvd.models import Alert

ENDP_PATH = "/alert_video"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "Return the MP4 clip for alert id via ?id= (PUR_CAP_BASIC_USER + ALERT_VIEW).",
}

# Hik clips can be tens of MB; refuse absurd sizes.
_MAX_VIDEO_BYTES = 256 * 1024 * 1024


def _query_arg(query, key: str) -> str | None:
    if not query:
        return None
    value = query.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return str(value)


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_ALERT_VIEW)
@api_endp
def impl_GET(headers, query=None):
    raw = _query_arg(query, "id")
    if raw is None or not str(raw).strip():
        return (400, {"error": "id is required"})
    try:
        video_id = int(str(raw).strip())
    except ValueError:
        return (400, {"error": "id must be an integer"})

    with state.app_db.session_factory() as session:
        alert = session.get(Alert, video_id)
        if alert is None:
            return (404, {"error": f"alert {video_id} not found"})
        path = Path(alert.path)

    if not path.is_file():
        return (404, {"error": "video file missing on disk"})
    size = path.stat().st_size
    if size <= 0:
        return (404, {"error": "video file is empty"})
    if size > _MAX_VIDEO_BYTES:
        return (413, {"error": "video file too large"})

    try:
        data = path.read_bytes()
    except OSError as e:
        return (500, {"error": f"failed to read video: {e}"})

    return {
        "rc": 200,
        "data": data,
        "content-type": "video/mp4",
        "cache-control": "private, max-age=3600",
        "headers": {
            "Accept-Ranges": "none",
            "Content-Disposition": f'inline; filename="alert-{video_id}.mp4"',
        },
    }
