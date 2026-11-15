"""Helpers to add / modify / delete rows in the ``config`` table."""

from __future__ import annotations

from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from hvd.models import ConfigEntry


class ConfigError(Exception):
    """Raised when a config helper operation fails."""

    def __init__(self, message: str, *, status: int = 400):
        super().__init__(message)
        self.status = status


def _require_nonempty(name: str, value: str) -> None:
    if name is None or not str(name).strip():
        raise ConfigError("entry name must not be empty")
    if value is None or not str(value).strip():
        raise ConfigError("entry value must not be empty")


class ConfigStore:
    def __init__(self, session_factory: Callable, *, default_group_id: int):
        self._session_factory = session_factory
        self._default_group_id = default_group_id

    def add(
        self,
        name: str,
        value: str,
        *,
        group_read: int | None = None,
        group_write: int | None = None,
        protected: bool = False,
    ) -> dict:
        _require_nonempty(name, value)
        name = str(name).strip()
        value = str(value).strip()
        gid_r = group_read if group_read is not None else self._default_group_id
        gid_w = group_write if group_write is not None else self._default_group_id
        with self._session_factory() as session:
            existing = session.scalar(
                select(ConfigEntry).where(
                    ConfigEntry.name == name,
                    ConfigEntry.group_read == gid_r,
                )
            )
            if existing is not None:
                raise ConfigError(
                    f"config entry '{name}' already exists for this group",
                    status=409,
                )
            row = ConfigEntry(
                name=name,
                value=value,
                group_read=gid_r,
                group_write=gid_w,
                protected=protected,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as e:
                session.rollback()
                raise ConfigError(
                    f"config entry '{name}' already exists for this group",
                    status=409,
                ) from e
            return self._to_dict(row)

    def modify(
        self,
        name: str,
        value: str,
        *,
        group_read: int,
        allow_protected: bool = False,
    ) -> dict:
        _require_nonempty(name, value)
        name = str(name).strip()
        value = str(value).strip()
        with self._session_factory() as session:
            row = session.scalar(
                select(ConfigEntry).where(
                    ConfigEntry.name == name,
                    ConfigEntry.group_read == group_read,
                )
            )
            if row is None:
                raise ConfigError(f"config entry '{name}' does not exist", status=404)
            if row.protected and not allow_protected:
                raise ConfigError(f"config entry '{name}' is protected", status=403)
            row.value = value
            session.commit()
            return self._to_dict(row)

    def delete(
        self,
        name: str,
        *,
        group_read: int,
        allow_protected: bool = False,
    ) -> None:
        name = str(name).strip() if name else ""
        if not name:
            raise ConfigError("entry name must not be empty")
        with self._session_factory() as session:
            row = session.scalar(
                select(ConfigEntry).where(
                    ConfigEntry.name == name,
                    ConfigEntry.group_read == group_read,
                )
            )
            if row is None:
                raise ConfigError(f"config entry '{name}' does not exist", status=404)
            if row.protected and not allow_protected:
                raise ConfigError(f"config entry '{name}' is protected", status=403)
            session.delete(row)
            session.commit()

    def get(self, name: str, *, group_read: int | None = None) -> dict | None:
        name = str(name).strip() if name else ""
        with self._session_factory() as session:
            q = select(ConfigEntry).where(ConfigEntry.name == name)
            if group_read is not None:
                q = q.where(ConfigEntry.group_read == group_read)
            row = session.scalar(q)
            return None if row is None else self._to_dict(row)

    def list_all(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.scalars(select(ConfigEntry).order_by(ConfigEntry.name)).all()
            return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(row: ConfigEntry) -> dict:
        return {
            "name": row.name,
            "value": row.value,
            "group_read": row.group_read,
            "group_write": row.group_write,
            "protected": bool(row.protected),
        }
