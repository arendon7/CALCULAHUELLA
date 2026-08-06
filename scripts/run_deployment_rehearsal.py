from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import argparse
import json

from sqlalchemy import select

from app.database import AppUser, Organization, SessionLocal, init_db
from app.deployment_readiness import run_deployment_rehearsal


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensayo de despliegue controlado de Calcula tu Huella")
    parser.add_argument("--strict", action="store_true", help="Exigir PostgreSQL, almacenamiento externo, HTTPS y secretos")
    parser.add_argument("--organization-id", type=int, default=0)
    parser.add_argument("--performed-by", default="operacion-local")
    parser.add_argument("--notes", default="Ejecutado mediante comando macOS")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as session:
        organization_id = args.organization_id or session.scalar(select(Organization.id).order_by(Organization.id))
        if not organization_id:
            print(json.dumps({"ok": False, "error": "No existe una organización"}, ensure_ascii=False))
            return 2
        performer = args.performed_by
        if performer == "operacion-local":
            performer = session.scalar(select(AppUser.email).where(
                AppUser.organization_id == organization_id,
                AppUser.role == "Administrador",
            ).order_by(AppUser.id)) or performer
        rehearsal = run_deployment_rehearsal(
            session,
            int(organization_id),
            performer,
            strict=args.strict,
            notes=args.notes,
        )
        session.commit()
        payload = {
            "ok": rehearsal.status == "Aprobado",
            "status": rehearsal.status,
            "score": rehearsal.score,
            "strict_mode": rehearsal.strict_mode,
            "database_backend": rehearsal.database_backend,
            "storage_backend": rehearsal.storage_backend,
            "rehearsal_id": rehearsal.id,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
