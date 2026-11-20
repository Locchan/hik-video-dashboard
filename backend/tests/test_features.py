from __future__ import annotations

import json
from http.client import HTTPConnection

from hvd.features import FEAT_ALERT_VIEW, FEAT_CONFIG, FEAT_STREAMING
from purest.auth.policy import DEFAULT_ROOT_PASSWORD
from sqlalchemy import inspect


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
    try:
        return resp.status, json.loads(body) if body else {}
    except json.JSONDecodeError:
        return resp.status, body


def _login(port, username, password):
    status, body = _post(port, "/auth/login", {"username": username, "password": password})
    assert status == 200, body
    return body["token"]


def test_features_table_seeded(hvd_app):
    _, app_db = hvd_app
    assert inspect(app_db.engine).has_table("features")
    feats = {f["name"]: f for f in app_db.feature_store.list_features()}
    assert FEAT_CONFIG in feats
    assert FEAT_ALERT_VIEW in feats
    assert FEAT_STREAMING in feats
    assert feats[FEAT_CONFIG]["enabled"] is True
    assert feats[FEAT_STREAMING]["enabled"] is False


def test_features_list_and_admin_toggle(hvd_app):
    rest, app_db = hvd_app
    token = _login(rest, "root", DEFAULT_ROOT_PASSWORD)
    from tests.conftest import auth_cookie

    auth = auth_cookie("root", token)

    status, body = _req(rest, "GET", "/features", headers=auth)
    assert status == 200, body
    names = [f["name"] for f in body["features"]]
    assert FEAT_CONFIG in names
    assert FEAT_ALERT_VIEW in names

    status, body = _req(
        rest,
        "UPDATE",
        f"/features?name={FEAT_CONFIG}&enabled=false",
        headers=auth,
    )
    assert status == 200, body
    assert body["enabled"] is False
    assert app_db.feature_store.is_enabled(FEAT_CONFIG) is False

    status, _ = _req(rest, "GET", "/config", headers=auth)
    assert status == 405

    status, body = _req(
        rest,
        "UPDATE",
        f"/features?name={FEAT_CONFIG}&enabled=true",
        headers=auth,
    )
    assert status == 200, body
    status, body = _req(rest, "GET", "/config", headers=auth)
    assert status == 200, body
