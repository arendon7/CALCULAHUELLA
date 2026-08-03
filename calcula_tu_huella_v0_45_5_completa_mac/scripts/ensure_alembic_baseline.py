#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

REVISION_BY_RELEASE = {
    "022": "20260731_0012",
    "023": "20260731_0013",
    "024": "20260731_0014",
    "025": "20260731_0015",
    "026": "20260801_0016",
    "027": "20260801_0017",
    "028": "20260801_0018",
    "029": "20260802_0019",
    "030": "20260802_0019",
    "031": "20260802_0019",
    "032": "20260802_0020",
    "033": "20260802_0021",
}


def release_hint(text: str) -> str | None:
    match = re.search(r"v?0?_?((?:2[2-9])|(?:3[0-3]))(?:\D|$)", text.casefold())
    return match.group(1) if match else None


def infer_revision(tables: set[str]) -> str | None:
    if "pilot_source_comparisons" in tables:
        return REVISION_BY_RELEASE["033"]
    if "base_year_recalculations" in tables:
        return REVISION_BY_RELEASE["032"]
    if "operational_import_profiles" in tables:
        return REVISION_BY_RELEASE["029"]
    if "period_closes" in tables:
        return REVISION_BY_RELEASE["028"]
    if "data_import_batches" in tables:
        return REVISION_BY_RELEASE["026"]
    if "pilot_executions" in tables:
        return REVISION_BY_RELEASE["025"]
    if "login_attempts" in tables:
        return REVISION_BY_RELEASE["024"]
    if "greenatics_pilots" in tables:
        return REVISION_BY_RELEASE["023"]
    if "methodology_source_documents" in tables:
        return REVISION_BY_RELEASE["022"]
    return None


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Uso: ensure_alembic_baseline.py BASE.sqlite [PISTA_VERSION]", file=sys.stderr)
        return 2
    database = Path(sys.argv[1]).expanduser().resolve()
    hint_text = sys.argv[2] if len(sys.argv) == 3 else database.name
    if not database.exists() or database.stat().st_size == 0:
        print("Base nueva: Alembic creará el esquema desde cero.")
        return 0
    with sqlite3.connect(database) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables:
            print("Base vacía: Alembic creará el esquema desde cero.")
            return 0
        if "alembic_version" in tables:
            row = db.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
            if row and row[0]:
                print(f"Línea base Alembic existente: {row[0]}")
                return 0
        hinted = release_hint(hint_text)
        revision = REVISION_BY_RELEASE.get(hinted or "") or infer_revision(tables)
        if not revision:
            print("No fue posible inferir una línea base segura para la base existente.", file=sys.stderr)
            return 1
        db.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)")
        db.execute("DELETE FROM alembic_version")
        db.execute("INSERT INTO alembic_version(version_num) VALUES (?)", (revision,))
        db.commit()
        print(f"Base existente identificada como V0.{hinted or 'inferida'}; Alembic se marcó en {revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
