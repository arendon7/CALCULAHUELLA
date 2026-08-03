from __future__ import annotations

import argparse
import json
import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.demo_environment import certify_demo_environment, ensure_demo_environment


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara y certifica el entorno demostrativo V0.45.")
    parser.add_argument("--prepare-only", action="store_true", help="Prepara datos sin generar certificado.")
    parser.add_argument("--performed-by", default="comando-mac-demo")
    args = parser.parse_args()
    if not settings.seed_demo:
        print("El modo demo está desactivado. Configura SEED_DEMO=true fuera de producción.")
        return 2
    init_db()
    with SessionLocal() as session:
        result = ensure_demo_environment(session)
        certification = None
        if not args.prepare_only:
            certification = certify_demo_environment(
                session,
                int(result["organizations"][0]),
                args.performed_by,
                "Preparación y certificación desde comando macOS.",
            )
        session.commit()
        output = {
            "version": settings.version,
            "organizations": result["summary"]["organizations"],
            "totals": result["summary"]["totals"],
            "certification": {
                "status": certification.status,
                "hash": certification.certificate_hash,
                "artifact": certification.artifact_name,
            } if certification else None,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        return 0 if not certification or certification.status == "Certificado demo" else 1


if __name__ == "__main__":
    raise SystemExit(main())
