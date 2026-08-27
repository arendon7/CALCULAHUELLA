from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.alembic_revision_authority import repository_head_revision

LEGACY_REVISION = "20260806_0038"
WORK_TABLES = {
    "work_items",
    "work_item_events",
    "work_item_links",
    "work_item_dependencies",
}


def _column_length(inspector, table: str, column: str) -> int | None:
    item = next(value for value in inspector.get_columns(table) if value["name"] == column)
    return getattr(item["type"], "length", None)


def _runtime_settings() -> tuple[str, Path]:
    database_url = os.environ["POSTGRES_LEGACY_DATABASE_URL"]
    artifact_dir = Path(
        os.environ.get("SERVERLESS_STAGING_ARTIFACT_DIR", "serverless-staging-artifacts")
    ).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return database_url, artifact_dir


def main() -> None:
    database_url, artifact_dir = _runtime_settings()
    expected_head_revision = repository_head_revision(ROOT)
    engine = create_engine(database_url, pool_pre_ping=True)

    # Crear una réplica estructural del ORM vigente para simular la base histórica
    # sin copiar datos reales. Después retiramos únicamente las tablas que sabemos
    # ausentes en Supabase y fijamos la revision observada 20260806_0038.
    os.environ["DATABASE_URL"] = database_url
    from app.db.base import Base
    import app.db.models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        for table in ("work_item_dependencies", "work_item_links", "work_item_events", "work_items"):
            connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        connection.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES (:revision)"),
            {"revision": LEGACY_REVISION},
        )

    before = inspect(engine)
    before_tables = set(before.get_table_names())
    password_before = _column_length(before, "app_users", "password_hash")
    methodology_before = _column_length(before, "methodology_source_documents", "status")
    if WORK_TABLES & before_tables:
        raise AssertionError("La réplica legado todavía contiene tablas work_items")
    if password_before is None or password_before < 255:
        raise AssertionError(f"password_hash legado inesperado: {password_before}")
    if methodology_before is None or methodology_before < 160:
        raise AssertionError(f"status metodológico legado inesperado: {methodology_before}")

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    # Una segunda ejecución debe ser un no-op seguro sobre el head alcanzado.
    second = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    after = inspect(engine)
    after_tables = set(after.get_table_names())
    password_after = _column_length(after, "app_users", "password_hash")
    methodology_after = _column_length(after, "methodology_source_documents", "status")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one()

    if not WORK_TABLES <= after_tables:
        raise AssertionError(f"Faltan work tables tras upgrade: {sorted(WORK_TABLES - after_tables)}")
    if password_after is None or password_after < password_before:
        raise AssertionError(f"password_hash perdió capacidad: {password_before} -> {password_after}")
    if methodology_after is None or methodology_after < methodology_before:
        raise AssertionError(f"status metodológico perdió capacidad: {methodology_before} -> {methodology_after}")
    if revision != expected_head_revision:
        raise AssertionError(
            "Revision final inesperada: "
            f"{revision}; head autoritativo del repositorio: {expected_head_revision}"
        )

    evidence = {
        "engine": "PostgreSQL",
        "legacy_revision": LEGACY_REVISION,
        "head_revision": revision,
        "repository_head_revision": expected_head_revision,
        "password_hash_length": {"before": password_before, "after": password_after},
        "methodology_status_length": {"before": methodology_before, "after": methodology_after},
        "work_tables_created": sorted(WORK_TABLES),
        "second_upgrade": "success",
        "upgrade_stdout_tail": upgrade.stdout[-1000:],
        "second_upgrade_stdout_tail": second.stdout[-500:],
    }
    (artifact_dir / "postgres-legacy-migration-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
