from __future__ import annotations

import json
from http.client import HTTPConnection

from purest.auth.policy import DEFAULT_ROOT_PASSWORD

from tests.conftest import auth_cookie


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
    status, body = _post(port, "/auth/login", {"username": username, "password": password})
    assert status == 200, body
    return body["token"]


def test_config_acl_create_update_delete(hvd_app):
    rest, app_db = hvd_app
    b = app_db.auth_backend

    root_token = _login(rest, "root", DEFAULT_ROOT_PASSWORD)
    status, body = _post(
        rest,
        "/auth/create_user",
        {"username": "alicecfg", "password": "password12"},
        headers=auth_cookie("root", root_token),
    )
    assert status == 200, body
    alice_token = _login(rest, "alicecfg", "password12")

    from sqlalchemy import select

    with b._session_factory() as session:
        alice_group = session.scalar(select(b.Group).where(b.Group.name == "alicecfg"))
        assert alice_group is not None
        assert "PUR_CAP_BASIC_USER" in (alice_group.capabilities or "")

    status, body = _req(
        rest,
        "PUT",
        "/config?entry_name=secret&value=s1",
        headers=auth_cookie("root", root_token),
    )
    assert status in (200, 201), body
    assert body.get("group_name") == "root"

    status, body = _req(
        rest,
        "PUT",
        "/config?entry_name=language&value=en",
        headers=auth_cookie("alicecfg", alice_token),
    )
    assert status in (200, 201), body
    assert body.get("group_name") == "alicecfg"

    status, body = _req(
        rest,
        "GET",
        "/config",
        headers=auth_cookie("root", root_token),
    )
    assert status == 200, body
    languages = [e for e in body.get("entries", []) if e.get("name") == "language"]
    # Root can see every group's language row; each carries group_name.
    by_group = {e.get("group_name"): e for e in languages}
    assert "alicecfg" in by_group
    assert by_group["alicecfg"]["group_read"] == alice_group.id

    status, body = _req(
        rest,
        "GET",
        "/config",
        headers=auth_cookie("alicecfg", alice_token),
    )
    assert status == 200, body
    # Alice must not see root's secret.
    names = {e.get("name") for e in body.get("entries", [])}
    assert "secret" not in names
