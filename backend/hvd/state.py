"""Process-wide handles set at boot."""

from __future__ import annotations

from hvd.db import AppDb

app_db: AppDb | None = None
