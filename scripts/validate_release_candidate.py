from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = _PROJECT_ROOT
# La validación estructural debe ser autónoma. No hereda la base abierta por
# pytest, la aplicación o una instalación activa, evitando contención SQLite.
_VALIDATION_INSTANCE = Path(
    os.environ.get("VALIDATION_INSTANCE_DIR", ROOT / ".final_validation_instance")
).resolve()
os.environ["INSTANCE_DIR"] = str(_VALIDATION_INSTANCE)
os.environ["DATABASE_URL"] = f"sqlite:///{_VALIDATION_INSTANCE / 'validation.db'}"
os.environ["SEED_DEMO"] = "0"
os.environ["SCHEDULER_ENABLED"] = "0"

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import settings
from app.database import Base
from app.main import app, templates

FORBIDDEN_NAMES = {"calculatuhuella.db", ".env", "session.key"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", "instance", ".final_validation_instance"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_candidate() -> dict[str, object]:
    invalid_files: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            continue
        if path.is_file() and (path.name in FORBIDDEN_NAMES or path.suffix == ".pyc"):
            invalid_files.append(str(rel))
    template_names = templates.env.list_templates(filter_func=lambda name: name.endswith(".html"))
    template_errors: list[str] = []
    for name in template_names:
        try:
            templates.env.get_template(name)
        except Exception as exc:
            template_errors.append(f"{name}: {exc}")
    config = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    heads = list(script.get_heads())
    required_docs = (
        "ACTA_CIERRE_V1_0_0.md",
        "APROBACION_METODOLOGICA_V1_CARLOS_URIBE.md",
        "APROBACION_JURIDICA_V1_AGUSTIN_RENDON.md",
        "INFORME_PILOTO_INTERNO_GREENATICS_V1.md",
        "INFORME_PILOTO_INTERNO_SEGUNDO_SECTOR_V1.md",
        "REVISION_SEGURIDAD_INTERNA_OWASP_ASVS_V1.md",
        "GUIA_LANZAMIENTO_CONTROLADO_V1.md",
    )
    required_legal = (
        "app/legal_web.py",
        "app/templates/legal_document.html",
    )
    checks = [
        {"code": "version", "ok": settings.version == "1.0.0", "detail": settings.version},
        {"code": "routes", "ok": len(app.routes) >= 320, "detail": len(app.routes)},
        {"code": "models", "ok": len(Base.registry.mappers) >= 120, "detail": len(Base.registry.mappers)},
        {"code": "templates", "ok": len(template_names) >= 80 and not template_errors, "detail": {"count": len(template_names), "errors": template_errors}},
        {"code": "migration_head", "ok": len(heads) == 1, "detail": heads},
        {"code": "clean_tree", "ok": not invalid_files, "detail": invalid_files},
        {"code": "internal_acceptance", "ok": all((ROOT / name).is_file() for name in required_docs), "detail": list(required_docs)},
        {"code": "legal_surface", "ok": all((ROOT / name).is_file() for name in required_legal), "detail": list(required_legal)},
        {
            "code": "controlled_release_defaults",
            "ok": (
                settings.final_methodology_internal_approved
                and settings.final_legal_internal_approved
                and settings.final_greenatics_internal_pilot_approved
                and settings.final_second_sector_internal_pilot_approved
            ),
            "detail": "Aprobaciones internas explícitas",
        },
        {
            "code": "public_production_conservative",
            "ok": not (
                settings.rc_windows_10_approved
                or settings.rc_windows_11_approved
                or settings.rc_security_review_approved
                or settings.final_infrastructure_approved
            ),
            "detail": "La producción pública no se declara por defecto",
        },
    ]
    return {
        "application": settings.app_name,
        "version": settings.version,
        "status": "passed" if all(item["ok"] for item in checks) else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida Calcula tu Huella V1.0.0 final para despliegue controlado.")
    parser.add_argument("--record-passed", action="store_true")
    parser.add_argument("--test-count", type=int, default=0)
    parser.add_argument("--duration-seconds", type=float, default=0.0)
    args = parser.parse_args()
    payload = inspect_candidate()
    if args.record_passed:
        if payload["status"] != "passed" or args.test_count <= 0:
            raise SystemExit("No se puede registrar evidencia aprobada sin controles internos y conteo de pruebas.")
        payload.update({
            "status": "passed",
            "test_count": args.test_count,
            "duration_seconds": args.duration_seconds if args.duration_seconds > 0 else None,
            "duration_note": "Ejecución distribuida en procesos aislados; no se consolidó una duración comparable." if args.duration_seconds <= 0 else None,
            "scope": "regresión automatizada, aceptación interna y controles estructurales",
            "release_class": "V1.0 final para despliegue controlado",
            "limitations": [
                "No acredita instalación física en Windows 10/11.",
                "No acredita auditoría de seguridad independiente.",
                "No acredita la infraestructura pública hasta que sus servicios reales sean certificados.",
                "La aprobación metodológica interna no equivale a verificación de un inventario particular.",
            ],
        })
        release_dir = ROOT / "release"
        release_dir.mkdir(exist_ok=True)
        evidence_path = release_dir / "FINAL_TEST_EVIDENCE.json"
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        payload["evidence_sha256"] = _sha256(evidence_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
