"""GET /thumbnail?video= — cached PNG for an alert clip."""

from __future__ import annotations

from purest import api_endp, auth, feat_req
from purest.auth import PUR_CAP_BASIC_USER

from hvd import state
from hvd.alerts import get_or_create_thumbnail_png
from hvd.alerts.thumbnails import ThumbnailError
from hvd.features import FEAT_ALERT_VIEW

ENDP_PATH = "/thumbnail"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "Return (and cache) a quarter-size PNG thumbnail for ?video=<alert id>.",
}


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
    raw = _query_arg(query, "video")
    if raw is None or not str(raw).strip():
        return (400, {"error": "video id is required"})
    try:
        video_id = int(str(raw).strip())
    except ValueError:
        return (400, {"error": "video id must be an integer"})
    try:
        png, timestamp, camera = get_or_create_thumbnail_png(
            state.app_db.session_factory,
            video_id=video_id,
        )
    except ThumbnailError as e:
        return (404, {"error": str(e)})
    etag = f'"{camera}-{timestamp.isoformat()}"'
    return {
        "rc": 200,
        "data": png,
        "content-type": "image/png",
        "cache-control": "public, max-age=86400",
        "headers": {"ETag": etag},
    }
