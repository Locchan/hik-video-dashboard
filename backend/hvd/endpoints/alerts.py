"""GET /alerts — scan clips, upsert DB, return list newer→older."""

from __future__ import annotations

from purest import api_endp, auth, feat_req
from purest.auth import PUR_CAP_BASIC_USER

from hvd import state
from hvd.alerts import sync_alerts_to_db
from hvd.features import FEAT_ALERT_VIEW

ENDP_PATH = "/alerts"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "Scan ALERTS_DIR clips, upsert into alert table, return newer→older list.",
}


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_ALERT_VIEW)
@api_endp
def impl_GET(headers, query=None):
    rows = sync_alerts_to_db(state.app_db.session_factory)
    return {"alerts": rows}
