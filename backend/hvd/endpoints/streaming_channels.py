"""GET /streaming/channels — DVR channel list (ISAPI) with config display names."""

from __future__ import annotations

from purest import api_endp, auth, feat_req, get_config
from purest.auth import PUR_CAP_BASIC_USER

from hvd import state
from hvd.features import FEAT_STREAMING
from hvd.streaming.dvr import list_dvrs_with_channels

ENDP_PATH = "/streaming/channels"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": (
        "List STREAMING_DVR_* devices and their ISAPI Streaming channels. "
        "Secrets stay server-side; names come from root config."
    ),
}


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_STREAMING)
@api_endp
def impl_GET(headers):
    _ = headers
    cfg = get_config()
    store = state.app_db.config_store
    # Root-owned DVR keys are not visible to normal users via /config — read all rows here.
    entries = store.list_all()
    return list_dvrs_with_channels(entries, logger=cfg.logger)
