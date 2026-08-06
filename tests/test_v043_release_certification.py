from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.database import (
    Base,
    ENGINE,
    OperationalIncident,
    ReleaseCertification,
    SessionLocal,
    init_db,
)
from app.deployment_readiness import production_checks, sync_incidents
from app.main import app
from app.release_certification import CERTIFICATION_DIR, resolve_certification_artifact


@pytest.fixture(autouse=True)
def fresh_database_v043():
    for path in CERTIFICATION_DIR.glob("certificacion_*.zip"):
        path.unlink(missing_ok=True)
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v043_local_certification_creates_signed_evidence_without_productive_claim():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        login(client)
        response = client.post(
            "/operacion/certificacion/ejecutar",
            data={"notes": "Validación local automatizada"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        payload = client.get("/api/operacion/certificacion").json()
        assert payload["available"] is True
        assert payload["status"] == "Validación local"
        assert payload["production_approved"] is False

    with SessionLocal() as session:
        certification = session.scalar(select(ReleaseCertification).order_by(ReleaseCertification.id.desc()))
        assert certification is not None
        assert certification.scope == "Local"
        assert len(certification.certificate_hash) == 64
        assert len(certification.artifact_sha256) == 64
        evidence = json.loads(certification.evidence_json)
        assert evidence["application_version"] == "1.0.0"
        assert evidence["production_approved"] is False
        artifact = resolve_certification_artifact(certification.artifact_name)
        with zipfile.ZipFile(artifact) as bundle:
            assert {"certificacion.json", "respaldo_manifest.json", "restauracion.json", "despliegue.json", "LEEME.txt"}.issubset(bundle.namelist())
            packaged = json.loads(bundle.read("certificacion.json"))
        assert packaged["certificate_hash"] == certification.certificate_hash


def test_v043_strict_certification_is_blocked_without_real_external_services():
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion/certificacion/ejecutar",
            data={"strict_mode": "on", "notes": "No simular aprobación"},
            follow_redirects=False,
        )
        assert response.status_code == 303
    with SessionLocal() as session:
        certification = session.scalar(select(ReleaseCertification).order_by(ReleaseCertification.id.desc()))
        assert certification is not None
        assert certification.scope == "Producción"
        assert certification.status == "Bloqueada"
        assert certification.production_approved is False
        blockers = json.loads(certification.blockers_json)
        codes = {item["code"] for item in blockers}
        assert "external_replication" in codes or "deployment_gate" in codes


def test_v043_deployment_incidents_auto_resolve_when_check_recovers():
    with SessionLocal() as session:
        checks = [{"code": "postgresql", "label": "PostgreSQL", "ok": False, "critical": True, "detail": "No disponible"}]
        sync_incidents(session, 1, checks)
        session.commit()
        incident = session.scalar(select(OperationalIncident))
        assert incident is not None and incident.status == "Abierto"

        sync_incidents(session, 1, [{"code": "postgresql", "label": "PostgreSQL", "ok": True, "critical": True, "detail": "Disponible"}])
        session.commit()
        session.refresh(incident)
        assert incident.status == "Resuelto"
        assert incident.resolved_by == "sistema-v0.45"


def test_v043_external_service_probes_are_part_of_strict_gate(monkeypatch):
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.deployment_readiness.urlopen", lambda request, timeout: Response())
    originals = {
        "object_storage_health_url": settings.object_storage_health_url,
        "prometheus_health_url": settings.prometheus_health_url,
        "alertmanager_health_url": settings.alertmanager_health_url,
        "grafana_health_url": settings.grafana_health_url,
    }
    try:
        for name in originals:
            object.__setattr__(settings, name, f"http://service/{name}")
        checks = production_checks(strict=True)
        service_checks = {item["code"]: item for item in checks if item["code"].endswith("_service")}
        assert set(service_checks) == {"object_storage_service", "prometheus_service", "alertmanager_service", "grafana_service"}
        assert all(item["ok"] and item["critical"] for item in service_checks.values())
    finally:
        for name, value in originals.items():
            object.__setattr__(settings, name, value)


def test_v043_operations_page_exposes_certification_section():
    with TestClient(app) as client:
        login(client)
        response = client.get("/operacion")
        assert response.status_code == 200
        assert "Evidencia operativa de la versión" in response.text
        assert "Generar certificación" in response.text


def test_v043_alertmanager_resolved_event_closes_incident():
    original = settings.alert_webhook_secret
    object.__setattr__(settings, "alert_webhook_secret", "v043-alert-secret")
    try:
        with TestClient(app) as client:
            firing = client.post(
                "/api/operacion/alertas",
                headers={"X-Alert-Secret": "v043-alert-secret"},
                json={"organization_id": 1, "title": "Latencia alta", "detail": "p95 > 2s", "severity": "Alta", "status": "firing"},
            )
            assert firing.status_code == 200
            resolved = client.post(
                "/api/operacion/alertas",
                headers={"X-Alert-Secret": "v043-alert-secret"},
                json={"organization_id": 1, "title": "Latencia alta", "detail": "p95 > 2s", "severity": "Alta", "status": "resolved"},
            )
            assert resolved.status_code == 200
        with SessionLocal() as session:
            incident = session.scalar(select(OperationalIncident).where(OperationalIncident.title == "Latencia alta"))
            assert incident is not None
            assert incident.status == "Resuelto"
            assert incident.resolved_by == "alertmanager"
    finally:
        object.__setattr__(settings, "alert_webhook_secret", original)


def test_v043_operational_scripts_bootstrap_project_path(tmp_path: Path):
    project_dir = Path(__file__).resolve().parents[1]
    script = project_dir / "scripts" / "certify_release.py"
    source = script.read_text(encoding="utf-8")
    assert "Certificación operativa" in source
    assert "_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]" in source
    for operational_script in project_dir.joinpath("scripts").glob("*.py"):
        source = operational_script.read_text(encoding="utf-8")
        if "from app." in source or "import app." in source:
            assert "_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]" in source
