from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select

from app.database import Base, ENGINE, Inventory, SessionLocal, init_db
from app.delivery_readiness import professional_delivery_summary
from app.main import app
from app.pilot_execution import guided_workspace
from app.reporting import create_report_artifact, generate_decision_brief_pdf


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v047_summary_exposes_publication_decision_and_owned_plan():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.id == 1))
        summary = professional_delivery_summary(session, inventory)
        assert summary["publication"]["level"]
        assert isinstance(summary["publication"]["can_share_external"], bool)
        assert summary["decision"]["primary_decision"]
        assert 0 <= summary["decision"]["confidence_score"] <= 100
        assert all(item["owner"] and item["acceptance"] for item in summary["gates"])
        assert all(item["priority"] and item["owner"] for item in summary["action_plan"])
        assert summary["metrics"]["ready_gates"] + summary["metrics"]["progress_gates"] + summary["metrics"]["blocked_gates"] == 8


def test_v047_guided_journey_includes_reduction_as_its_own_stage():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.id == 1))
        user = {"role": "Consultor", "organization_id": inventory.organization_id}
        workspace = guided_workspace(session, user, inventory)
        names = [item["name"] for item in workspace["milestones"]]
        assert names == ["Configurar", "Recolectar", "Calcular", "Revisar", "Reducir", "Reportar"]
        assert workspace["total"] == 6


def test_v047_page_and_api_make_shareability_explicit():
    with TestClient(app) as client:
        login(client)
        page = client.get("/entrega-profesional")
        assert page.status_code == 200
        assert "SALA DE DECISIÓN" in page.text
        assert "NIVEL DE PUBLICACIÓN" in page.text
        assert "PLAN PRIORIZADO DE CIERRE" in page.text
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "ESTADO DE USO" in dashboard.text
        payload = client.get("/api/entrega-profesional/resumen").json()
        assert payload["publication"]["level"]
        assert payload["decision"]["primary_decision"]
        assert isinstance(payload["action_plan"], list)


def test_v047_decision_brief_is_generated_and_registered(tmp_path: Path):
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.id == 1))
        output = tmp_path / "ficha.pdf"
        generate_decision_brief_pdf(session, inventory, output)
        reader = PdfReader(str(output))
        assert len(reader.pages) == 1
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Ficha ejecutiva para decisión" in text
        assert "Control de publicación" in text
        artifact = create_report_artifact(session, inventory, "ficha", "consultor@calculatuhuella.local")
        assert artifact.report_type == "Ficha ejecutiva"
        assert artifact.file_name.endswith(".pdf")
