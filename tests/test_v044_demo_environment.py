from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    Base,
    DemoEnvironmentCertification,
    ENGINE,
    Facility,
    Organization,
    SessionLocal,
    init_db,
)
from app.demo_environment import demo_environment_summary, resolve_demo_certificate
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_v044():
    Base.metadata.drop_all(ENGINE)
    init_db()
    yield


def login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v044_seeds_greenatics_and_andinas_with_complete_demo_workflows():
    with SessionLocal() as session:
        summary = demo_environment_summary(session)
        assert summary["organization_count"] == 2
        by_name = {row["trade_name"]: row for row in summary["organizations"]}
        assert set(by_name) == {"Greenatics", "Industrias Andinas"}
        assert by_name["Greenatics"]["activity_records"] >= 100
        assert by_name["Greenatics"]["calculations"] > 0
        assert by_name["Greenatics"]["requests"] >= 4
        assert by_name["Greenatics"]["notifications"] >= 4
        assert by_name["Greenatics"]["support_tickets"] >= 2
        assert by_name["Industrias Andinas"]["calculations"] > 0
        greenatics = session.scalar(select(Organization).where(Organization.trade_name == "Greenatics"))
        sites = set(session.scalars(select(Facility.name).where(Facility.organization_id == greenatics.id)))
        assert {"Planta Yarumal", "Planta Támesis", "Oficina Medellín"}.issubset(sites)


def test_v044_demo_center_can_switch_between_companies():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "0.45.5"
        login(client)
        page = client.get("/entorno-demo")
        assert page.status_code == 200
        assert "Greenatics y Andinas" in page.text
        with SessionLocal() as session:
            greenatics_id = session.scalar(select(Organization.id).where(Organization.trade_name == "Greenatics"))
        response = client.post(f"/portafolio/cambiar/{greenatics_id}", follow_redirects=False)
        assert response.status_code == 303
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "Greenatics" in dashboard.text
        information = client.get("/informacion")
        assert information.status_code == 200
        assert "Transporte contratado" in information.text or "solicitudes" in information.text.lower()


def test_v044_demo_certification_creates_signed_json_artifact():
    with TestClient(app) as client:
        login(client)
        response = client.post("/entorno-demo/certificar", data={"notes": "Prueba V0.45"}, follow_redirects=False)
        assert response.status_code == 303
    with SessionLocal() as session:
        certification = session.scalar(select(DemoEnvironmentCertification).order_by(DemoEnvironmentCertification.id.desc()))
        assert certification is not None
        assert certification.status == "Certificado demo"
        assert len(certification.certificate_hash) == 64
        artifact = resolve_demo_certificate(certification.artifact_name)
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        assert payload["status"] == "Certificado demo"
        assert payload["certificate_hash"] == certification.certificate_hash
        assert len(payload["checks"]) >= 8


def test_v044_demo_preparation_is_idempotent():
    with TestClient(app) as client:
        login(client)
        first = client.post("/entorno-demo/preparar", follow_redirects=False)
        second = client.post("/entorno-demo/preparar", follow_redirects=False)
        assert first.status_code == second.status_code == 303
    with SessionLocal() as session:
        summary = demo_environment_summary(session)
        assert summary["organization_count"] == 2
        assert summary["totals"]["activity_records"] == 152


def test_v044_mac_demo_command_is_self_contained():
    root = Path(__file__).resolve().parents[1]
    command = root / "15_PREPARAR_Y_CERTIFICAR_DEMO.command"
    script = root / "scripts" / "prepare_demo_environment.py"
    assert command.exists() and command.stat().st_mode & 0o111
    assert "SEED_DEMO=\"true\"" in command.read_text(encoding="utf-8")
    assert "_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]" in script.read_text(encoding="utf-8")
