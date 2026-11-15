"""Feature flags: code registry + DB enabled state.

Descriptions live in this module (developer-facing English). Frontend shows
translated titles/descriptions via i18n keys ``feature.<NAME>.title`` /
``feature.<NAME>.desc``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import select

from hvd.models import FeatureFlag

# --- Registry (add new features here) -----------------------------------------


@dataclass(frozen=True)
class FeatureDef:
    name: str
    description: str
    default_enabled: bool = False


FEAT_CONFIG = "CONFIG"
FEAT_ALERT_VIEW = "ALERT_VIEW"

FEATURES: dict[str, FeatureDef] = {
    FEAT_CONFIG: FeatureDef(
        name=FEAT_CONFIG,
        description=(
            "Group configuration key/value store: list, create, update, and delete "
            "config entries in the configuration window."
        ),
        default_enabled=True,
    ),
    FEAT_ALERT_VIEW: FeatureDef(
        name=FEAT_ALERT_VIEW,
        description=(
            "Browse camera alert clips under ALERTS_DIR, with nearest-snap thumbnails "
            "in the Alerts page."
        ),
        default_enabled=True,
    ),
}


def known_feature_names() -> list[str]:
    return sorted(FEATURES.keys())


# --- Store --------------------------------------------------------------------


class FeatureStore:
    """Read/write ``features`` rows; seed missing registry entries."""

    def __init__(self, session_factory: Callable):
        self._session_factory = session_factory

    def seed_defaults(self) -> None:
        with self._session_factory() as session:
            existing = {
                row.name: row
                for row in session.scalars(select(FeatureFlag)).all()
            }
            dirty = False
            for name, spec in FEATURES.items():
                if name in existing:
                    continue
                session.add(
                    FeatureFlag(name=name, enabled=spec.default_enabled)
                )
                dirty = True
            if dirty:
                session.commit()

    def is_enabled(self, name: str) -> bool:
        if name not in FEATURES:
            return False
        with self._session_factory() as session:
            row = session.get(FeatureFlag, name)
            if row is None:
                return FEATURES[name].default_enabled
            return bool(row.enabled)

    def list_features(self) -> list[dict]:
        """All registry features with current enabled flag + code description."""
        with self._session_factory() as session:
            rows = {
                r.name: r
                for r in session.scalars(select(FeatureFlag)).all()
            }
        out = []
        for name in known_feature_names():
            spec = FEATURES[name]
            row = rows.get(name)
            enabled = bool(row.enabled) if row is not None else spec.default_enabled
            out.append(
                {
                    "name": name,
                    "enabled": enabled,
                    "description": spec.description,
                    "default_enabled": spec.default_enabled,
                }
            )
        return out

    def set_enabled(self, name: str, enabled: bool) -> dict | None:
        if name not in FEATURES:
            return None
        with self._session_factory() as session:
            row = session.get(FeatureFlag, name)
            if row is None:
                row = FeatureFlag(name=name, enabled=enabled)
                session.add(row)
            else:
                row.enabled = enabled
            session.commit()
            session.refresh(row)
            spec = FEATURES[name]
            return {
                "name": row.name,
                "enabled": bool(row.enabled),
                "description": spec.description,
                "default_enabled": spec.default_enabled,
            }
