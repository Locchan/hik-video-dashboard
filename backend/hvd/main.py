"""Entry point: wire DB_* env → purest AuthProvider engine → REST API only."""

from __future__ import annotations

import logging
import os
import sys

from purest import configure, serve

from hvd import state
from hvd.db import init_db
from hvd.endpoints import ENDPOINTS


def _logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO,
        format="%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
    )
    return logging.getLogger("hvd")


def main(argv: list[str] | None = None) -> None:
    _ = argv or sys.argv[1:]
    logger = _logger()
    app_db = init_db(logger=logger)
    state.app_db = app_db
    logger.info(
        "DB ready via purest provider %s (dialect=%s)",
        type(app_db.provider).__name__,
        app_db.provider.dialect_name,
    )
    feature_store = app_db.feature_store
    configure(
        auth_backend=app_db.auth_backend,
        logger=logger,
        server_version=f"hvd/{os.environ.get('HVD_VERSION', '0.1.0')}",
        rest_workers=int(os.environ.get("REST_WORKERS", "4")),
        builtin_auth_endpoints=True,
        # Behind nginx, /api/ is stripped; clients call /api/auth/* → upstream /auth/*.
        auth_endpoint_prefix="/auth/",
        feature_enabled=feature_store.is_enabled,
        auth_cookie_user="hvd_user",
        auth_cookie_token="hvd_token",
    )
    rest_port = int(os.environ.get("REST_PORT", "8080"))
    ws_port = int(os.environ.get("WS_PORT", "8081"))
    logger.info("Starting purest on REST=%s WS=%s", rest_port, ws_port)
    serve(rest_port, ws_port, ENDPOINTS)


if __name__ == "__main__":
    main()
