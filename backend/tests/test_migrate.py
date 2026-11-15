from __future__ import annotations

from pathlib import Path

from hvd.migrate import list_migration_files, split_sql


def test_split_sql_ignores_comments_and_strings():
    script = """
    -- leading comment
    ALTER TABLE t ADD COLUMN a INTEGER;
    /* block
       comment */
    UPDATE t SET b = 'a;b' WHERE c = "x;y";
    """
    stmts = split_sql(script)
    assert len(stmts) == 2
    assert "ADD COLUMN a INTEGER" in stmts[0]
    assert "'a;b'" in stmts[1]


def test_list_migration_files_sorted(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("nope", encoding="utf-8")
    (tmp_path / "20261115160000_b.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "20261115150000_a.sql").write_text("SELECT 1;", encoding="utf-8")
    names = [p.name for p in list_migration_files(tmp_path)]
    assert names == ["20261115150000_a.sql", "20261115160000_b.sql"]
