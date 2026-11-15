"""GET / UPDATE /api/features — list flags; admin toggles enabled."""

from __future__ import annotations

from purest import api_endp, auth, get_config
from purest.auth import PUR_CAP_ADMIN, PUR_CAP_BASIC_USER, auth_username

from hvd import state
from hvd.acl import is_admin
from hvd.features import FEATURES

ENDP_PATH = "/features"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "List registered features with enabled state and code descriptions.",
    "UPDATE": "Enable/disable a feature via ?name=&enabled= (PUR_CAP_ADMIN).",
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


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


@auth(PUR_CAP_BASIC_USER)
@api_endp
def impl_GET(headers, query=None):
    store = state.app_db.feature_store
    return {"features": store.list_features()}


@auth(PUR_CAP_ADMIN)
@api_endp
def impl_UPDATE(headers, query=None):
    username = auth_username(headers)
    backend = get_config().auth_backend
    if not is_admin(backend, username):
        return (403, {"error": "Insufficient permissions"})
    name = _query_arg(query, "name")
    enabled_raw = _query_arg(query, "enabled")
    if not name or not str(name).strip():
        return (400, {"error": "feature name must not be empty"})
    name = str(name).strip()
    if name not in FEATURES:
        return (404, {"error": f"unknown feature '{name}'"})
    enabled = _parse_bool(enabled_raw)
    if enabled is None:
        return (400, {"error": "enabled must be true or false"})
    updated = state.app_db.feature_store.set_enabled(name, enabled)
    return updated
