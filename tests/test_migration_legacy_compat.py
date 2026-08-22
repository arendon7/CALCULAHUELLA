from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
LEGACY_REVISION = "20260806_0038"
HEAD_REVISION = "20260812_0040"
WORK_TABLES = {
    "work_items",
    "work_item_events",
    "work_item_links",
    "work_item_dependencies",
}


def _run_python(code: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_migration_graph_contains_live_checkpoint_and_single_head(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'graph.db'}"
    history = subprocess.run(
        [sys.executable, "-m", "alembic", "history"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    heads = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert LEGACY_REVISION in history
    assert "20260810_0038" in history
    assert "20260810_0039" in history
    assert heads.count("(head)") == 1
    assert HEAD_REVISION in heads


def test_live_like_0038_database_upgrades_without_shrinking_or_schema_bootstrap(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-live-like.db"
    database_url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "APP_ENV": "staging",
            "INSTANCE_DIR": str(tmp_path / "instance"),
            "SEED_DEMO": "false",
            "SCHEDULER_ENABLED": "false",
            "EMAIL_BACKEND": "disabled",
            "STORAGE_BACKEND": "local",
        }
    )

    # Construye el esquema ORM vigente únicamente para fabricar una réplica
    # estructural controlada; luego elimina work_items y la estampa como la
    # revision histórica observada en Supabase. El upgrade posterior sí lo hace
    # Alembic y debe recuperar exclusivamente lo que falta.
    _run_python(
        "from app.db.base import Base, ENGINE; import app.db.models; Base.metadata.create_all(ENGINE)",
        env,
    )

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in ("work_item_dependencies", "work_item_links", "work_item_events", "work_items"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)")
        conn.execute("DELETE FROM alembic_version")
        conn.execute("INSERT INTO alembic_version(version_num) VALUES (?)", (LEGACY_REVISION,))
        conn.commit()

    before = inspect(create_engine(database_url))
    assert not (WORK_TABLES & set(before.get_table_names()))
    assert next(c for c in before.get_columns("app_users") if c["name"] == "password_hash")["type"].length >= 255
    assert next(
        c for c in before.get_columns("methodology_source_documents") if c["name"] == "status"
    )["type"].length >= 160

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    after = inspect(create_engine(database_url))
    assert WORK_TABLES <= set(after.get_table_names())
    assert next(c for c in after.get_columns("app_users") if c["name"] == "password_hash")["type"].length >= 255
    assert next(
        c for c in after.get_columns("methodology_source_documents") if c["name"] == "status"
    )["type"].length >= 160
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == HEAD_REVISION
