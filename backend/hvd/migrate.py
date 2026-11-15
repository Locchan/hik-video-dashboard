"""PostgreSQL migration runner for HVD.

Migration files live in ``backend/migrations/*.sql`` (PostgreSQL SQL).
Local / non-Postgres boots skip this entirely — see ``init_db``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_VERSION_RE = re.compile(r"^(\d{14})_.+\.sql$", re.IGNORECASE)

_BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) NOT NULL PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


class MigrationError(RuntimeError):
    """Failed to apply a migration."""


def migrations_dir(path: Path | None = None) -> Path:
    return path if path is not None else MIGRATIONS_DIR


def list_migration_files(directory: Path | None = None) -> list[Path]:
    """Return pending-candidate ``.sql`` files sorted by version prefix."""
    root = migrations_dir(directory)
    if not root.is_dir():
        return []
    files = []
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        if _VERSION_RE.match(entry.name):
            files.append(entry)
    return sorted(files, key=lambda p: p.name)


def split_sql(script: str) -> list[str]:
    """Split a SQL script into statements on ``;`` outside quotes/comments."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":
                buf.append(nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            buf.append(ch)
            if ch == '"' and nxt == '"':
                buf.append(nxt)
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if ch == "-" and nxt == "-":
            buf.append(ch)
            buf.append(nxt)
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            buf.append(ch)
            buf.append(nxt)
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            stmt = _strip_sql_comments("".join(buf)).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = _strip_sql_comments("".join(buf)).strip()
    if tail:
        statements.append(tail)
    return statements


def _strip_sql_comments(sql: str) -> str:
    """Remove comment-only noise so empty comment blocks don't become statements."""
    # Keep it simple: drop full-line -- comments after split already handled strings.
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    text_out = "\n".join(lines)
    text_out = re.sub(r"/\*.*?\*/", "", text_out, flags=re.DOTALL)
    return text_out.strip()


def _ensure_migrations_table(conn) -> None:
    conn.execute(text(_BOOTSTRAP_SQL))


def _applied_versions(conn) -> set[str]:
    rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {row[0] for row in rows}


def run_migrations(
    engine: Engine,
    *,
    directory: Path | None = None,
    logger: logging.Logger | None = None,
) -> list[str]:
    """Apply pending ``*.sql`` migrations. Returns versions applied this call."""
    log = logger or logging.getLogger("hvd.migrate")
    root = migrations_dir(directory)
    applied_now: list[str] = []

    with engine.begin() as conn:
        _ensure_migrations_table(conn)
        done = _applied_versions(conn)

        for path in list_migration_files(root):
            version = path.name
            if version in done:
                continue
            script = path.read_text(encoding="utf-8")
            statements = split_sql(script)
            log.info("Applying migration %s (%d statement(s))", version, len(statements))
            try:
                for stmt in statements:
                    conn.execute(text(stmt))
                conn.execute(
                    text(
                        "INSERT INTO schema_migrations (version) VALUES (:version)"
                    ),
                    {"version": version},
                )
            except Exception as e:
                raise MigrationError(f"Migration {version} failed: {e}") from e
            applied_now.append(version)
            log.info("Applied migration %s", version)

    if not applied_now:
        log.info("Migrations up to date (%s)", root)
    return applied_now
