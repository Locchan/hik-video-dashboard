from __future__ import annotations

import pytest

from hvd.db import UnsupportedDatabaseError, require_postgres


def test_require_postgres_allows_postgresql_dialect():
    require_postgres(db_type="postgresql", dialect_name="postgresql+psycopg2")


def test_require_postgres_rejects_sqlite():
    with pytest.raises(UnsupportedDatabaseError, match="PostgreSQL-only"):
        require_postgres(db_type="sqlite", dialect_name="sqlite+pysqlite")
