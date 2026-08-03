from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import Base, ENGINE, init_db
from app.main import app
from app.product_experience import journey_detail, navigation_for


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(ENGINE)
    init_db()
    yield


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_navigation_defaults_to_inventory_core() -> None:
    user = {
        "role": "Consultor",
        "capabilities": {
            "manage_inventory", "manage_sources", "view_methodology", "review",
            "manage_supply_chain", "manage_consolidation", "view_consolidation",
        },
    }
    navigation = navigation_for(user, "essential")
    labels = [item["label"] for section in navigation["core"] for item in section["items"]]
    assert "Mi trabajo" in labels
    assert "Recorrido del inventario" in labels
    assert "Datos y evidencias" in labels
    assert "Cierre metodológico" in labels
    assert navigation["advanced"] == []
    assert navigation["internal"] == []


def test_complete_navigation_preserves_advanced_capabilities() -> None:
    user = {
        "role": "Administrador",
        "capabilities": {
            "manage_org", "manage_inventory", "manage_sources", "view_methodology",
            "manage_methodology_governance", "manage_operations", "manage_saas",
            "manage_portfolio", "manage_consolidation", "view_consolidation",
        },
    }
    navigation = navigation_for(user, "complete")
    advanced = [item["label"] for section in navigation["advanced"] for item in section["items"]]
    internal = [item["label"] for section in navigation["internal"] for item in section["items"]]
    assert "Metodología" in advanced
    assert "Biblioteca Colombia" in advanced
    assert "Organización" in internal
    assert "Operación y seguridad" in internal
    assert "Consolidación V1.0" in internal


def test_dashboard_switches_between_essential_and_complete_view() -> None:
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        essential = client.get("/dashboard")
        assert essential.status_code == 200
        assert "Vista esencial" in essential.text
        assert "Herramientas avanzadas" not in essential.text
        assert "Recorrido del inventario" in essential.text

        response = client.post(
            "/preferencias/vista",
            data={"mode": "complete", "return_url": "/dashboard"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        complete = client.get("/dashboard")
        assert "Vista completa" in complete.text
        assert "Herramientas avanzadas" in complete.text
        assert "Administración interna" in complete.text


def test_inventory_journey_has_five_decision_stages() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        response = client.get("/recorrido-inventario")
        assert response.status_code == 200
        for stage in ["Configurar", "Recolectar", "Calcular", "Revisar", "Reportar"]:
            assert stage in response.text
        assert "Responsable de información" in response.text
        assert "Un solo proceso, cinco etapas" in response.text


def test_dashboard_uses_calculated_monthly_data_not_placeholder_trend() -> None:
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "▼ 8,4%" not in response.text
        assert "periodo seleccionado" in response.text
        assert "monthly-chart" in response.text or "Aún no hay resultados mensuales calculados" in response.text


def test_journey_detail_marks_only_one_current_stage() -> None:
    workspace = {
        "score": 20,
        "completed": 1,
        "total": 5,
        "actions": [],
        "milestones": [
            {"name": "Configurar", "done": True, "detail": "OK", "href": "/inventarios/1"},
            {"name": "Recolectar", "done": False, "detail": "2/5", "href": "/informacion"},
            {"name": "Calcular", "done": False, "detail": "0/5", "href": "/calculos"},
            {"name": "Revisar", "done": False, "detail": "Pendiente", "href": "/control"},
            {"name": "Reportar", "done": False, "detail": "0", "href": "/reportes"},
        ],
    }
    journey = journey_detail(workspace, "Consultor")
    current = [step for step in journey["steps"] if step["current"]]
    assert len(current) == 1
    assert current[0]["name"] == "Recolectar"
