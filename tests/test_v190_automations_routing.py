from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import ScheduledAutomation, SessionLocal
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

AUTOMATION_ROUTES = {
    ("GET", "/automatizaciones"),
    ("POST", "/automatizaciones/nueva"),
    ("POST", "/automatizaciones/{automation_id}/estado"),
    ("POST", "/automatizaciones/{automation_id}/ejecutar"),
    ("POST", "/automatizaciones/procesar-vencidas"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_automations_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/automations_web.py").read_text(encoding="utf-8")
    assert '@app.get("/automatizaciones"' not in main_source
    assert '@app.post("/automatizaciones/' not in main_source
    assert "register_automation_routes(" in main_source
    assert module_source.count("@app.") == 5
    for authority in ("calculate_next_run", "execute_automation", "process_due_automations"):
        assert authority in module_source
    assert "def _compliance_score" not in module_source


def test_v190_automation_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in AUTOMATION_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == AUTOMATION_ROUTES
    assert len(actual) == len(AUTOMATION_ROUTES)


def test_v190_automation_permissions_and_creation_persist():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/automatizaciones").status_code == 403
        client.post("/logout")
        _login(client, "consultor@calculatuhuella.local")
        page = client.get("/automatizaciones")
        assert page.status_code == 200
        response = client.post(
            "/automatizaciones/nueva",
            data={
                "name": "Automatización V1.9",
                "automation_type": "Recordatorio de solicitudes",
                "cadence": "Semanal",
                "schedule_time": "08:00",
                "inventory_id": "1",
                "weekday": "1",
                "days_before": "3",
                "recipient_roles": ["Administrador", "Consultor"],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as session:
        row = session.scalar(select(ScheduledAutomation).where(ScheduledAutomation.name == "Automatización V1.9"))
        assert row is not None
        assert row.active is True
        assert row.next_run_at is not None
        assert row.timezone == "America/Bogota"
