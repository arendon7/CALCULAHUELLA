from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import Base, ENGINE, init_db
from app.main import app
from app.onboarding_experience import onboarding_summary

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def test_onboarding_summary_prioritizes_in_progress_step():
    rows = [
        SimpleNamespace(code="ORG-01", title="Organización", description="A", status="Completado", owner="Cliente", due_date=None, display_order=10),
        SimpleNamespace(code="MET-01", title="Metodología", description="B", status="En progreso", owner="Consultor", due_date=None, display_order=30),
        SimpleNamespace(code="DAT-01", title="Datos", description="C", status="Pendiente", owner="Cliente", due_date=None, display_order=40),
    ]
    summary = onboarding_summary(rows, inventory_id=7)
    assert summary["score"] == 33
    assert summary["next_step"]["row"].code == "MET-01"
    assert summary["next_step"]["href"] == "/inventarios/7"
    assert summary["next_step"]["current"] is True


def test_diagnosis_is_a_four_step_accessible_wizard():
    template = (ROOT / "app" / "templates" / "public_diagnosis.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert template.count("data-diagnosis-step=") == 4
    assert "data-diagnosis-progress" in template
    assert "data-diagnosis-back" in template
    assert "data-diagnosis-submit" in template
    assert "initializeDiagnosisWizard" in javascript
    assert "reportValidity" in javascript


def test_onboarding_is_visible_in_essential_navigation():
    product_experience = (ROOT / "app" / "product_experience.py").read_text(encoding="utf-8")
    assert '_item("Configuración inicial", "/onboarding", "onboarding", "▶")' in product_experience


def test_public_and_authenticated_guided_surfaces_render():
    with TestClient(app) as client:
        diagnosis = client.get("/diagnostico")
        assert diagnosis.status_code == 200
        assert "Paso 1 de 4" in diagnosis.text
        login = client.post(
            "/login",
            data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        onboarding = client.get("/onboarding")
        dashboard = client.get("/dashboard")
        assert onboarding.status_code == 200
        assert "Seis actividades, un resultado operativo" in onboarding.text
        assert dashboard.status_code == 200
        assert "CONTEXTO DEL INVENTARIO" in dashboard.text
        assert "Configuración completa ✓" in dashboard.text
