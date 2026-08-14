from __future__ import annotations

import re

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import DataRequest, EmissionSource, Inventory, SessionLocal
from app.demo_environment import demo_environment_summary
from app.main import app
from app.product_experience import navigation_for


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _labels(role: str, capabilities: set[str]) -> list[str]:
    navigation = navigation_for({"role": role, "capabilities": capabilities}, "essential")
    return [item["label"] for section in navigation["core"] for item in section["items"]]


def test_iteration12_each_role_has_a_distinct_short_work_menu() -> None:
    labels = {
        "Cliente": _labels("Cliente", {"view_inventory", "provide_data", "view_results"}),
        "Consultor": _labels(
            "Consultor",
            {"manage_inventory", "manage_sources", "manage_activity_data", "review", "view_results"},
        ),
        "Revisor": _labels("Revisor", {"review", "view_methodology", "view_results"}),
        "Verificador": _labels(
            "Verificador", {"external_audit", "review", "view_methodology", "view_results"}
        ),
        "Administrador": _labels(
            "Administrador",
            {"manage_portfolio", "manage_org", "manage_sources", "review", "view_results"},
        ),
    }
    assert all(5 <= len(items) <= 8 for items in labels.values())
    assert labels["Cliente"] != labels["Verificador"]
    assert "Cargar datos" in labels["Cliente"]
    assert "Aseguramiento" in labels["Verificador"]
    assert "Portafolio de empresas" in labels["Administrador"]


def test_iteration12_dashboard_integrates_status_and_mobile_actions() -> None:
    with TestClient(app) as client:
        login(client)
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert 'class="inventory-pulse card"' in page.text
        assert 'class="mobile-taskbar"' in page.text
        assert "Configuración completa ✓" in page.text
        assert "Continuar recorrido" in page.text
        assert "EMPIEZA AQUÍ · TU SIGUIENTE ACCIÓN" in page.text
        assert "TU RUTA DE TRABAJO" in page.text
        assert 'class="journey-progress"' in page.text
        assert "Del dato al informe, sin perder el hilo" in page.text


def test_iteration12_client_receives_an_action_the_client_can_complete() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert "Atender solicitudes de información" in page.text
        assert "Abrir pendientes" in page.text
        assert "Responsable de información" in page.text
        assert "Continúa desde aquí" in page.text
        assert "Resolver revisión" not in page.text


def test_iteration12_completed_requests_do_not_drive_client_next_action() -> None:
    with SessionLocal() as session:
        inventory = session.scalar(
            select(Inventory).where(Inventory.organization_id == 1).order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        assert inventory is not None
        requests = list(session.scalars(select(DataRequest).where(DataRequest.inventory_id == inventory.id)))
        assert requests
        for item in requests:
            item.status = "Completado"
        session.commit()

    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert "Atender solicitudes de información" not in page.text
        assert "Completar datos y evidencias" in page.text
        assert "Continuar captura" in page.text


def test_iteration12_information_defaults_to_twelve_recent_records() -> None:
    with TestClient(app) as client:
        login(client)
        page = client.get("/informacion")
        assert page.status_code == 200
        assert "Mostrando 12 de 44 registros" in page.text
        assert page.text.count('class="table-link"') == 12
        assert "Ver historial completo" in page.text

        complete = client.get("/informacion?show_all=true")
        assert complete.status_code == 200
        assert "Mostrando 44 de 44 registros" in complete.text
        assert complete.text.count('class="table-link"') == 44
        assert "Ver solo los más recientes" in complete.text


def test_iteration12_information_and_source_are_task_based() -> None:
    with TestClient(app) as client:
        login(client)
        information = client.get("/informacion")
        assert information.text.count("data-task-panel=") == 3
        assert 'data-task-tabs="information"' in information.text

        with SessionLocal() as session:
            source_id = session.scalar(select(EmissionSource.id).order_by(EmissionSource.id))
            assert source_id is not None
        source = client.get(f"/fuentes/{source_id}")
        assert source.status_code == 200
        assert source.text.count("data-task-panel=") >= 4
        assert 'data-task-tabs="source-detail"' in source.text
        assert "Seis preguntas antes de elegir un factor" in source.text


def test_iteration12_journey_uses_progressive_stage_disclosure() -> None:
    with TestClient(app) as client:
        login(client)
        page = client.get("/recorrido-inventario")
        assert page.status_code == 200
        assert "Tu ruta para completar el inventario" in page.text
        assert page.text.count("<details class=\"journey-stage-row") == 6
        assert page.text.count("data-exclusive-details=\"journey-stage\"") == 6
        open_stages = re.findall(r'<details class="journey-stage-row[^"]*"[^>]*\bopen\b', page.text)
        assert len(open_stages) <= 1


def test_iteration12_demo_portfolio_is_ready_to_navigate_not_empty() -> None:
    with SessionLocal() as session:
        summary = demo_environment_summary(session)
        assert summary["organization_count"] == 5
        assert all(row["profile_completion"] == 100 for row in summary["organizations"])
        assert all(row["activity_records"] > 0 for row in summary["organizations"])
        assert all(row["calculations"] > 0 for row in summary["organizations"])
        assert len({row["current_stage"] for row in summary["organizations"]}) >= 3
