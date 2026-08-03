from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.database import Organization, RestoreDrill, SessionLocal, add_audit, init_db
from app.operations import create_backup, rehearse_backup_restore


def main() -> int:
    init_db()
    backup = create_backup(created_by="comando-local", label="ensayo-restauracion")
    result = rehearse_backup_restore(Path(backup["path"]))
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        if organization:
            drill = RestoreDrill(
                organization_id=organization.id,
                backup_name=Path(backup["path"]).name,
                backup_sha256=str(result.get("backup_sha256", "")),
                application_version=str(result.get("application_version", "")),
                database_backend=str(result.get("database_backend", "")),
                status=str(result.get("status", "Fallido")),
                integrity_result=str(result.get("integrity_result", "")),
                table_count=int(result.get("table_count", 0) or 0),
                record_summary_json=json.dumps(result.get("record_summary", {}), ensure_ascii=False, sort_keys=True),
                checks_json=json.dumps(result.get("checks", {}), ensure_ascii=False, sort_keys=True),
                notes="; ".join(result.get("issues", [])),
                performed_by="comando-local",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_ms=int(result.get("duration_ms", 0) or 0),
            )
            session.add(drill)
            add_audit(
                session,
                organization.id,
                "comando-local",
                "ENSAYAR_RESTAURACION",
                "Respaldo",
                drill.backup_name,
                detail=f"Estado {drill.status} · integridad {drill.integrity_result} · {drill.table_count} tablas",
            )
            session.commit()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
