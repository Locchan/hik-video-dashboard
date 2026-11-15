"""GET / PUT (create) / UPDATE / DELETE /api/config with group ACL."""

from __future__ import annotations

from purest import api_endp, auth, feat_req, get_config
from purest.auth import PUR_CAP_BASIC_USER, auth_username

from hvd import state
from hvd.acl import can_read, can_write, is_privileged
from hvd.config_store import ConfigError
from hvd.features import FEAT_CONFIG

ENDP_PATH = "/config"
LOGIN_REQUIRED = True
DOCSTRING = {
    "GET": "List config entries visible to the caller, or one entry via ?entry_name=",
    "PUT": "Create a config entry via ?entry_name=&value= (attributed to caller's group)",
    "UPDATE": "Update an existing entry via ?entry_name=&value=",
    "DELETE": "Delete an existing entry via ?entry_name=",
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


def _find_visible(entries, name: str, backend, username: str, *, write: bool):
    check = can_write if write else can_read
    matches = [e for e in entries if e["name"] == name and check(backend, username, e)]
    return matches[0] if matches else None


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_CONFIG)
@api_endp
def impl_GET(headers, query=None):
    username = auth_username(headers)
    store = state.app_db.config_store
    backend = get_config().auth_backend
    entry_name = _query_arg(query, "entry_name")
    visible = [e for e in store.list_all() if can_read(backend, username, e)]
    if entry_name:
        entry = _find_visible(visible, entry_name, backend, username, write=False)
        if entry is None:
            return (404, {"error": f"config entry '{entry_name}' not found"})
        return entry
    return {"entries": visible}


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_CONFIG)
@api_endp
def impl_PUT(headers, query=None):
    """Create a new config entry for the caller's group."""
    username = auth_username(headers)
    store = state.app_db.config_store
    backend = get_config().auth_backend
    entry_name = _query_arg(query, "entry_name")
    value = _query_arg(query, "value")
    if entry_name is None or not str(entry_name).strip():
        return (400, {"error": "entry name must not be empty"})
    if value is None or not str(value).strip():
        return (400, {"error": "entry value must not be empty"})
    group_id = backend.get_user_group_id(username)
    if group_id is None:
        return (401, {"error": "Unauthorized"})
    # Reject duplicates visible to this user (same name in their group).
    existing = store.get(entry_name.strip(), group_read=group_id)
    if existing is not None:
        return (409, {"error": f"config entry '{entry_name.strip()}' already exists for this group"})
    try:
        created = store.add(
            entry_name,
            value,
            group_read=group_id,
            group_write=group_id,
        )
    except ConfigError as e:
        return (e.status, {"error": str(e)})
    return (201, created)


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_CONFIG)
@api_endp
def impl_UPDATE(headers, query=None):
    username = auth_username(headers)
    store = state.app_db.config_store
    backend = get_config().auth_backend
    entry_name = _query_arg(query, "entry_name")
    value = _query_arg(query, "value")
    if entry_name is None or not str(entry_name).strip():
        return (400, {"error": "entry name must not be empty"})
    if value is None or not str(value).strip():
        return (400, {"error": "entry value must not be empty"})
    entry = _find_visible(store.list_all(), entry_name.strip(), backend, username, write=True)
    if entry is None:
        # Distinguish missing vs no write permission among readable rows.
        readable = _find_visible(store.list_all(), entry_name.strip(), backend, username, write=False)
        if readable is not None:
            return (403, {"error": "Insufficient permissions"})
        return (404, {"error": f"config entry '{entry_name.strip()}' does not exist"})
    try:
        updated = store.modify(
            entry["name"],
            value,
            group_read=entry["group_read"],
            allow_protected=is_privileged(backend, username),
        )
    except ConfigError as e:
        return (e.status, {"error": str(e)})
    return updated


@auth(PUR_CAP_BASIC_USER)
@feat_req(FEAT_CONFIG)
@api_endp
def impl_DELETE(headers, query=None):
    username = auth_username(headers)
    store = state.app_db.config_store
    backend = get_config().auth_backend
    entry_name = _query_arg(query, "entry_name")
    if entry_name is None or not str(entry_name).strip():
        return (400, {"error": "entry name must not be empty"})
    entry = _find_visible(store.list_all(), entry_name.strip(), backend, username, write=True)
    if entry is None:
        readable = _find_visible(store.list_all(), entry_name.strip(), backend, username, write=False)
        if readable is not None:
            return (403, {"error": "Insufficient permissions"})
        return (404, {"error": f"config entry '{entry_name.strip()}' does not exist"})
    try:
        store.delete(
            entry["name"],
            group_read=entry["group_read"],
            allow_protected=is_privileged(backend, username),
        )
    except ConfigError as e:
        return (e.status, {"error": str(e)})
    return {"deleted": entry["name"]}
