from __future__ import annotations

import threading

import pytest

import purest.config as config_mod
import purest.server as server_mod
from purest import configure


@pytest.fixture(autouse=True)
def _reset_purest_globals():
    config_mod._CONFIG = None
    server_mod.endpoints = {}
    server_mod.ws_endpoints = {}
    server_mod._ws_listen_port = None
    yield
    config_mod._CONFIG = None
    server_mod.endpoints = {}
    server_mod.ws_endpoints = {}
    server_mod._ws_listen_port = None


@pytest.fixture
def free_ports():
    import socket

    def _one():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    return _one(), _one()


@pytest.fixture
def run_api_server(free_ports):
    rest_port, ws_port = free_ports
    holder = {"thread": None, "error": None}

    def _start(modules, **configure_kwargs):
        configure_kwargs.setdefault("builtin_auth_endpoints", False)
        configure(**configure_kwargs)

        def target():
            try:
                from purest import serve

                serve(rest_port, ws_port, modules, bind_host="127.0.0.1")
            except Exception as e:
                holder["error"] = e

        t = threading.Thread(target=target, name="test-api", daemon=True)
        holder["thread"] = t
        t.start()
        import socket
        import time

        deadline = time.time() + 5
        while time.time() < deadline:
            if holder["error"] is not None:
                raise holder["error"]
            try:
                with socket.create_connection(("127.0.0.1", rest_port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise TimeoutError("API server did not start")
        return rest_port, ws_port

    yield _start
