from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings

MIN_REGRESSION_TESTS = 386


def _load_test_evidence(project_dir: Path) -> dict[str, Any]:
    candidates = [
        project_dir / "release" / "FINAL_TEST_EVIDENCE.json",
        project_dir / "release" / "RC1_TEST_EVIDENCE.json",
    ]
    path = next((item for item in candidates if item.is_file()), candidates[0])
    if not path.is_file():
        return {"status": "missing", "test_count": 0, "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "test_count": 0, "path": str(path)}
    payload["path"] = str(path)
    return payload


def _gate(code: str, label: str, ok: bool, detail: str, *, group: str) -> dict[str, object]:
    return {"code": code, "label": label, "ok": bool(ok), "detail": detail, "group": group}


def release_candidate_summary(
    project_dir: Path,
    *,
    critical_open: int,
    approved_gates: int,
    gate_count: int,
    validated_journeys: int,
    journey_count: int,
) -> dict[str, object]:
    """Summarize V1.0 readiness without conflating controlled release and public production."""
    evidence = _load_test_evidence(project_dir)
    test_count = int(evidence.get("test_count", 0) or 0)
    tests_ok = evidence.get("status") == "passed" and test_count >= MIN_REGRESSION_TESTS

    package_checks = [
        _gate("V1-VERSION", "Versión final identificada", settings.version == "1.0.0", f"Versión activa: {settings.version}", group="Paquete"),
        _gate("V1-TESTS", "Regresión automatizada documentada", tests_ok, f"{test_count} pruebas · estado {evidence.get('status', 'missing')}", group="Paquete"),
        _gate("V1-SCOPE", "Alcance funcional congelado", (project_dir / "ACTA_CIERRE_V1_0_0.md").is_file(), "Acta de cierre y regla de comunicación", group="Paquete"),
        _gate("V1-LEGAL-PAGES", "Documentación legal incorporada", (project_dir / "APROBACION_JURIDICA_V1_AGUSTIN_RENDON.md").is_file(), "Términos, privacidad, DPA, SLA y limitaciones", group="Paquete"),
    ]
    governance_checks = [
        _gate("V1-CRITICAL", "Sin hallazgos críticos abiertos", critical_open == 0, f"{critical_open} hallazgos críticos abiertos", group="Gobierno"),
        _gate("V1-GATES", "Puertas de release aprobadas", gate_count > 0 and approved_gates == gate_count, f"{approved_gates}/{gate_count} puertas aprobadas", group="Gobierno"),
        _gate("V1-JOURNEYS", "Recorridos por rol aprobados", journey_count > 0 and validated_journeys == journey_count, f"{validated_journeys}/{journey_count} recorridos aprobados", group="Gobierno"),
    ]
    internal_checks = [
        _gate(
            "V1-CARLOS",
            "Revisión metodológica interna de Carlos",
            settings.final_methodology_internal_approved and (project_dir / "APROBACION_METODOLOGICA_V1_CARLOS_URIBE.md").is_file(),
            "Aprobación del diseño metodológico; no equivale a verificación de inventarios",
            group="Aceptación interna",
        ),
        _gate(
            "V1-LEGAL",
            "Revisión jurídica interna de Agustín",
            settings.final_legal_internal_approved and (project_dir / "APROBACION_JURIDICA_V1_AGUSTIN_RENDON.md").is_file(),
            "Base contractual aprobada; identidad productiva debe configurarse",
            group="Aceptación interna",
        ),
        _gate(
            "V1-GREENATICS",
            "Piloto funcional interno Greenatics",
            settings.final_greenatics_internal_pilot_approved and (project_dir / "INFORME_PILOTO_INTERNO_GREENATICS_V1.md").is_file(),
            "Escenario multisede y controles sectoriales con datos demostrativos",
            group="Aceptación interna",
        ),
        _gate(
            "V1-SECOND",
            "Piloto funcional interno multisectorial",
            settings.final_second_sector_internal_pilot_approved and (project_dir / "INFORME_PILOTO_INTERNO_SEGUNDO_SECTOR_V1.md").is_file(),
            "Validación de no sobreajuste con escenarios de servicios, industria y agro",
            group="Aceptación interna",
        ),
        _gate(
            "V1-SECURITY-INTERNAL",
            "Revisión interna de seguridad",
            (project_dir / "REVISION_SEGURIDAD_INTERNA_OWASP_ASVS_V1.md").is_file(),
            "Controles internos basados en OWASP ASVS; no es auditoría independiente",
            group="Aceptación interna",
        ),
    ]
    external_checks = [
        _gate("V1-WIN10", "Prueba física en Windows 10", settings.rc_windows_10_approved, "Debe ejecutarse en equipo Windows 10 real", group="Producción pública"),
        _gate("V1-WIN11", "Prueba física en Windows 11", settings.rc_windows_11_approved, "Debe ejecutarse en equipo Windows 11 real", group="Producción pública"),
        _gate("V1-SECURITY-EXT", "Prueba de seguridad independiente", settings.rc_security_review_approved, "Pentest o revisión independiente con riesgo residual", group="Producción pública"),
        _gate("V1-INFRA", "Infraestructura definitiva certificada", settings.final_infrastructure_approved, "PostgreSQL, almacenamiento, SMTP, TLS, monitoreo y restauración reales", group="Producción pública"),
        _gate(
            "V1-IDENTITY",
            "Identidad contractual productiva completa",
            bool(settings.legal_provider_nit and settings.legal_notice_address and "@" in settings.legal_contact_email and "@" in settings.privacy_contact_email),
            "NIT, dirección y canales jurídicos configurados",
            group="Producción pública",
        ),
    ]

    package_ready = all(item["ok"] for item in package_checks)
    governance_ready = all(item["ok"] for item in governance_checks)
    internal_ready = all(item["ok"] for item in internal_checks)
    controlled_release_ready = package_ready and governance_ready and internal_ready
    external_ready = all(item["ok"] for item in external_checks)
    production_ready = controlled_release_ready and external_ready

    if production_ready:
        status = "V1.0 final · producción pública"
    elif controlled_release_ready:
        status = "V1.0 final · despliegue controlado"
    elif package_ready:
        status = "V1.0 final · aceptación pendiente"
    else:
        status = "En preparación"

    all_checks = package_checks + governance_checks + internal_checks + external_checks
    return {
        "version": settings.version,
        "status": status,
        "package_ready": package_ready,
        "governance_ready": governance_ready,
        "internal_ready": internal_ready,
        "controlled_release_ready": controlled_release_ready,
        "external_ready": external_ready,
        "production_ready": production_ready,
        "package_checks": package_checks,
        "governance_checks": governance_checks,
        "internal_checks": internal_checks,
        "external_checks": external_checks,
        "checks": all_checks,
        "passed": sum(1 for item in all_checks if item["ok"]),
        "total": len(all_checks),
        "test_evidence": evidence,
    }
