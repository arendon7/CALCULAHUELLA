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
from app.release_certification import run_release_certification


def main() -> int:
    parser = argparse.ArgumentParser(description="Certificación operativa de una versión de Calcula tu Huella")
    parser.add_argument("--strict", action="store_true", help="Exigir dependencias productivas y réplica externa")
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
        certification = run_release_certification(
            session,
            int(organization_id),
            performer,
            strict=args.strict,
            notes=args.notes,
        )
        session.commit()
        payload = {
            "ok": certification.production_approved if args.strict else certification.status == "Validación local",
            "status": certification.status,
            "scope": certification.scope,
            "production_approved": certification.production_approved,
            "certificate_hash": certification.certificate_hash,
            "artifact_name": certification.artifact_name,
            "artifact_sha256": certification.artifact_sha256,
            "backup_name": certification.backup_name,
            "certification_id": certification.id,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
