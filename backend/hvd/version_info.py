"""Runtime version strings for GET /version."""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path

from hvd import __version__ as backend_version

# Shipped beside the backend image (see backend/Dockerfile). Env overrides.
_FRONTEND_VERSION_FILE = Path(
    os.environ.get("HVD_FRONTEND_VERSION_FILE", "/usr/local/share/hvd/FRONTEND_VERSION")
)


def purest_version() -> str:
    try:
        return pkg_version("purest")
    except PackageNotFoundError:
        try:
            import purest

            return getattr(purest, "__version__", "unknown")
        except Exception:
            return "unknown"


def _read_frontend_version_file() -> str | None:
    try:
        text = _FRONTEND_VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def frontend_version() -> str:
    env = (os.environ.get("HVD_FRONTEND_VERSION") or "").strip()
    if env:
        return env
    from_file = _read_frontend_version_file()
    if from_file:
        return from_file
    return "unknown"


def version_payload() -> dict[str, str]:
    return {
        "backend": backend_version,
        "frontend": frontend_version(),
        "purest": purest_version(),
    }
