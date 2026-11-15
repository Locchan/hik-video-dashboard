from __future__ import annotations

import json
from http.client import HTTPConnection

import pytest
from sqlalchemy import select

from hvd import state
from hvd.db import init_db
from hvd.endpoints import ENDPOINTS
from purest.auth.policy import DEFAULT_ROOT_PASSWORD


@pytest.fixture
def hvd_app(run_api_server, tmp_path):
    db_path = str(tmp_path / "hvd.sqlite")
    app_db = init_db(db_type="sqlite", url=db_path)
    state.app_db = app_db
    rest, _ = run_api_server(
        ENDPOINTS,
        auth_backend=app_db.auth_backend,
        builtin_auth_endpoints=True,
        auth_endpoint_prefix="/api/auth/",
    )
    return rest, app_db


def _post(port, path, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Content-Length": str(len(data))}
    if headers:
        hdrs.update(headers)
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", path, body=data, headers=hdrs)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, json.loads(body) if body else {}


def _req(port, method, path, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, json.loads(body) if body else {}


def _login(port, username, password):
    status, body = _post(port, "/api/auth/login", {"username": username, "password": password})
    assert status == 200, body
    return body["token"]


def test_config_acl_create_update_delete(hvd_app):
    rest, app_db = hvd_app
    b = app_db.auth_backend

    root_token = _login(rest, "root", DEFAULT_ROOT_PASSWORD)
    status, body = _post(
        rest,
        "/api/auth/create_user",
        {"username": "alice", "password": "password12"},
        headers={"Authorization": f"root, {root_token}"},
    )
    assert status == 200, body
    alice_token = _login(rest, "alice", "password12")

    with b._session_factory() as session:
        alice_group = session.scalar(select(b.Group).where(b.Group.name == "alice"))
        assert alice_group is not None
        alice_gid = alice_group.id

    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=secret&value=s1",
        headers={"Authorization": f"root, {root_token}"},
    )
    assert status == 201
    assert body["name"] == "secret"
    assert body["group_read"] == b.get_root_group_id()

    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=shared&value=v1",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 201
    assert body["group_read"] == alice_gid
    assert body["group_write"] == alice_gid

    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=&value=x",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 400
    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=x&value=",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 400

    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=shared&value=v9",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 409

    status, body = _req(
        rest,
        "PUT",
        "/api/config?entry_name=shared&value=root-copy",
        headers={"Authorization": f"root, {root_token}"},
    )
    assert status == 201

    status, body = _req(rest, "GET", "/api/config", headers={"Authorization": f"root, {root_token}"})
    assert status == 200
    assert {e["name"] for e in body["entries"]} >= {"secret", "shared"}

    status, body = _req(rest, "GET", "/api/config", headers={"Authorization": f"alice, {alice_token}"})
    assert status == 200
    assert {e["name"] for e in body["entries"]} == {"shared"}
    assert body["entries"][0]["value"] == "v1"

    status, body = _req(
        rest, "GET", "/api/config?entry_name=secret", headers={"Authorization": f"alice, {alice_token}"}
    )
    assert status == 404

    status, body = _req(
        rest,
        "UPDATE",
        "/api/config?entry_name=shared&value=v2",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 200
    assert body["value"] == "v2"

    status, body = _req(
        rest,
        "UPDATE",
        "/api/config?entry_name=secret&value=nope",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 404

    status, body = _req(
        rest,
        "UPDATE",
        "/api/config?entry_name=missing&value=x",
        headers={"Authorization": f"root, {root_token}"},
    )
    assert status == 404

    status, body = _req(
        rest,
        "DELETE",
        "/api/config?entry_name=shared",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 200
    assert body == {"deleted": "shared"}

    status, body = _req(
        rest,
        "DELETE",
        "/api/config?entry_name=shared",
        headers={"Authorization": f"alice, {alice_token}"},
    )
    assert status == 404
