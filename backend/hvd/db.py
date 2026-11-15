"""Database bootstrap: read DB_* env, build purest AuthProvider, share its engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from purest.auth import SqlAuthBackend, create_auth_models, make_auth_provider
from purest.auth.backends.provider import AuthProvider
from purest.auth.policy import DEFAULT_ROOT_PASSWORD

from hvd.config_store import ConfigStore
from hvd.models import Base, ConfigEntry


@dataclass
class AppDb:
    provider: AuthProvider
    engine: Engine
    session_factory: Callable
    auth_backend: SqlAuthBackend
    config_store: ConfigStore
    Base: type[DeclarativeBase]


def env_db_settings() -> dict:
    return {
        "db_type": os.environ.get("DB_TYPE", "sqlite"),
        "url": os.environ.get("DB_URL"),
        "username": os.environ.get("DB_USERNAME"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_DATABASE"),
        "odbc_driver": os.environ.get("DB_ODBC_DRIVER"),
        "root_password": os.environ.get("ROOT_PASSWORD", DEFAULT_ROOT_PASSWORD),
        "token_ttl_min": int(os.environ.get("TOKEN_TTL_MIN", "60")),
    }


def init_db(
    *,
    db_type: str | None = None,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    database: str | None = None,
    odbc_driver: str | None = None,
    root_password: str | None = None,
    token_ttl_min: int | None = None,
    logger=None,
) -> AppDb:
    """Create provider via purest, create auth + config tables, seed root, return handles."""
    settings = env_db_settings()
    provider = make_auth_provider(
        db_type if db_type is not None else settings["db_type"],
        url=url if url is not None else settings["url"],
        username=username if username is not None else settings["username"],
        password=password if password is not None else settings["password"],
        database=database if database is not None else settings["database"],
        odbc_driver=odbc_driver if odbc_driver is not None else settings["odbc_driver"],
    )
    engine = provider.get_engine()
    create_auth_models(Base)
    _ = ConfigEntry
    Base.metadata.create_all(engine)

    auth_backend = SqlAuthBackend(
        Base,
        provider=provider,
        token_ttl_min=token_ttl_min if token_ttl_min is not None else settings["token_ttl_min"],
        root_password=root_password if root_password is not None else settings["root_password"],
        logger=logger,
    )
    session_factory = auth_backend.session_factory()
    root_group_id = auth_backend.get_root_group_id()
    config_store = ConfigStore(session_factory, default_group_id=root_group_id)
    return AppDb(
        provider=provider,
        engine=engine,
        session_factory=session_factory,
        auth_backend=auth_backend,
        config_store=config_store,
        Base=Base,
    )
