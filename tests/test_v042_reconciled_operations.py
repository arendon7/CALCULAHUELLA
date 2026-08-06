from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.database import (
    Base,
    DeploymentRehearsal,
    ENGINE,
    OperationalIncident,
    SessionLocal,
    init_db,
)
from app.main import app
from app.storage import storage


@pytest.fixture(autouse=True)
def fresh_database_v043():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v043_health_architecture_and_storage_probe():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        probe = storage.verified_probe()
        assert probe["ok"] is True
        login(client)
        summary = client.get("/api/arquitectura/resumen").json()
    assert summary["persistence"]["model_class_count"] == 120
    assert summary["persistence"]["repository_count"] == 5
    assert summary["persistence"]["service_count"] == 5
    assert summary["owned_route_count"] >= 116
    assert summary["architecture_split_ok"] is True


def test_v043_local_rehearsal_is_audited_without_fake_external_approval():
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion/despliegue/ensayar",
            data={"notes": "Ensayo local automatizado"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        api = client.get("/api/operacion/preparacion")
        assert api.status_code == 200
        payload = api.json()
    with SessionLocal() as session:
        run = session.scalar(select(DeploymentRehearsal).order_by(DeploymentRehearsal.id.desc()))
        assert run is not None
        assert run.strict_mode is False
        assert run.status == "Aprobado"
        checks = json.loads(run.checks_json)
        assert any(item["code"] == "postgresql" and item["critical"] is False for item in checks)
        assert payload["ready"] is False  # La puerta productiva estricta sigue bloqueada.


def test_v043_strict_rehearsal_creates_deduplicated_incidents():
    with TestClient(app) as client:
        login(client)
        for _ in range(2):
            response = client.post(
                "/operacion/despliegue/ensayar",
                data={"strict_mode": "on", "notes": "Ensayo estricto"},
                follow_redirects=False,
            )
            assert response.status_code == 303
    with SessionLocal() as session:
        run = session.scalar(select(DeploymentRehearsal).order_by(DeploymentRehearsal.id.desc()))
        incidents = list(session.scalars(select(OperationalIncident)))
        assert run is not None and run.status == "Bloqueado"
        assert incidents
        assert any(item.occurrence_count >= 2 for item in incidents)
        assert any("PostgreSQL" in item.title or "Almacenamiento" in item.title for item in incidents)


def test_v043_metrics_endpoint_and_alert_webhook_authentication():
    with TestClient(app) as client:
        client.get("/api/health")
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "cth_http_requests_total" in metrics_response.text

        original = settings.alert_webhook_secret
        object.__setattr__(settings, "alert_webhook_secret", "test-alert-secret")
        try:
            denied = client.post("/api/operacion/alertas", json={"organization_id": 1, "title": "Prueba"})
            assert denied.status_code == 401
            accepted = client.post(
                "/api/operacion/alertas",
                headers={"X-Alert-Secret": "test-alert-secret"},
                json={
                    "organization_id": 1,
                    "title": "Servicio no disponible",
                    "detail": "Prueba de Alertmanager",
                    "severity": "Crítica",
                },
            )
            assert accepted.status_code == 200
            assert accepted.json()["ok"] is True
        finally:
            object.__setattr__(settings, "alert_webhook_secret", original)


def test_v043_database_transfer_reconciles_every_domain(tmp_path):
    from sqlalchemy import create_engine
    from app.config import settings as app_settings
    from app.database_transfer import database_inventory, transfer_database

    target_url = f"sqlite:///{tmp_path / 'target.db'}"
    target_engine = create_engine(target_url)
    Base.metadata.create_all(target_engine)
    target_engine.dispose()
    result = transfer_database(app_settings.database_url, target_url)
    assert result.reconciled is True
    assert result.copied_rows > 0
    assert result.table_counts == database_inventory(target_url)
    assert result.table_counts["organizations"] == 6
    assert result.table_counts["inventories"] == 7
