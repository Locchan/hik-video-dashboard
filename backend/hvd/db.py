"""Database bootstrap: PostgreSQL-only AuthProvider + migrations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from purest.auth import SqlAuthBackend, create_auth_models, make_auth_provider
from purest.auth.backends.provider import AuthProvider
from purest.auth.policy import DEFAULT_ROOT_PASSWORD, PUR_CAP_BASIC_USER, merge_capabilities

from hvd.config_store import ConfigStore
from hvd.features import FeatureStore
from hvd.language import LanguageAwareAuthBackend
from hvd.migrate import run_migrations
from hvd.models import Alert, AlertThumbnail, Base, ConfigEntry, FeatureFlag

POSTGRES_DB_TYPES = frozenset(
    {
        "postgresql",
        "postgres",
        "pg",
        "postgresql_odbc",
        "postgres_odbc",
        "pg_odbc",
    }
)


class UnsupportedDatabaseError(RuntimeError):
    """Raised when HVD is started against a non-PostgreSQL dialect."""


@dataclass
class AppDb:
    provider: AuthProvider
    engine: Engine
    session_factory: Callable
    auth_backend: SqlAuthBackend
    config_store: ConfigStore
    feature_store: FeatureStore
    Base: type[DeclarativeBase]


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _is_postgres_db_type(db_type: str | None) -> bool:
    return (db_type or "").strip().lower() in POSTGRES_DB_TYPES


def _is_postgres_dialect(dialect_name: str | None) -> bool:
    return (dialect_name or "").startswith("postgresql")


def require_postgres(*, db_type: str, dialect_name: str) -> None:
    """Crash unless dialect is PostgreSQL."""
    if _is_postgres_db_type(db_type) and _is_postgres_dialect(dialect_name):
        return
    if _is_postgres_dialect(dialect_name):
        return
    raise UnsupportedDatabaseError(
        "HVD is PostgreSQL-only "
        f"(got DB_TYPE={db_type!r}, dialect={dialect_name!r})."
    )


def backfill_basic_user_cap(auth_backend, logger=None) -> int:
    """Ensure every api_group includes PUR_CAP_BASIC_USER. Returns rows updated."""
    from sqlalchemy import select

    updated = 0
    with auth_backend._session_factory() as session:
        groups = session.scalars(select(auth_backend.Group)).all()
        for group in groups:
            merged = merge_capabilities(group.capabilities, PUR_CAP_BASIC_USER)
            if merged != group.capabilities:
                group.capabilities = merged
                updated += 1
        if updated:
            session.commit()
    if updated and logger is not None:
        logger.info("Backfilled PUR_CAP_BASIC_USER on %s group(s)", updated)
    return updated


def env_db_settings() -> dict:
    return {
        "db_type": os.environ.get("DB_TYPE", "postgresql"),
        "url": os.environ.get("DB_URL"),
        "username": os.environ.get("DB_USERNAME"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_DATABASE"),
        "odbc_driver": os.environ.get("DB_ODBC_DRIVER"),
        "root_password": os.environ.get("ROOT_PASSWORD", DEFAULT_ROOT_PASSWORD),
        "token_ttl_min": int(os.environ.get("TOKEN_TTL_MIN", "60")),
        "skip_migrations": _env_truthy("HVD_SKIP_MIGRATIONS"),
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
    skip_migrations: bool | None = None,
    logger=None,
) -> AppDb:
    """Create provider, create auth/app tables, run PG migrations, seed, return handles."""
    settings = env_db_settings()
    resolved_type = db_type if db_type is not None else settings["db_type"]
    skip_mig = (
        settings["skip_migrations"] if skip_migrations is None else bool(skip_migrations)
    )

    if not _is_postgres_db_type(resolved_type):
        raise UnsupportedDatabaseError(
            "HVD is PostgreSQL-only " f"(got DB_TYPE={resolved_type!r})."
        )

    provider = make_auth_provider(
        resolved_type,
        url=url if url is not None else settings["url"],
        username=username if username is not None else settings["username"],
        password=password if password is not None else settings["password"],
        database=database if database is not None else settings["database"],
        odbc_driver=odbc_driver if odbc_driver is not None else settings["odbc_driver"],
    )
    require_postgres(db_type=resolved_type, dialect_name=provider.dialect_name)
    engine = provider.get_engine()
    create_auth_models(Base)
    _ = ConfigEntry
    _ = FeatureFlag
    _ = Alert
    _ = AlertThumbnail
    Base.metadata.create_all(engine)

    if skip_mig:
        if logger is not None:
            logger.info("Skipping migrations (HVD_SKIP_MIGRATIONS)")
    else:
        run_migrations(engine, logger=logger)

    auth_backend = SqlAuthBackend(
        Base,
        provider=provider,
        token_ttl_min=token_ttl_min if token_ttl_min is not None else settings["token_ttl_min"],
        root_password=root_password if root_password is not None else settings["root_password"],
        logger=logger,
    )
    backfill_basic_user_cap(auth_backend, logger=logger)
    session_factory = auth_backend.session_factory()
    root_group_id = auth_backend.get_root_group_id()
    config_store = ConfigStore(session_factory, default_group_id=root_group_id)
    feature_store = FeatureStore(session_factory)
    feature_store.seed_defaults()
    auth_backend = LanguageAwareAuthBackend(auth_backend, config_store)
    return AppDb(
        provider=provider,
        engine=engine,
        session_factory=session_factory,
        auth_backend=auth_backend,
        config_store=config_store,
        feature_store=feature_store,
        Base=Base,
    )
