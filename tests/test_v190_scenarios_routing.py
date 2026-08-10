from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

SCENARIO_ROUTES = {
    ("GET", "/escenarios"),
    ("POST", "/escenarios/nuevo"),
    ("POST", "/escenarios/{scenario_id}/configurar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_scenarios_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/scenarios_web.py").read_text(encoding="utf-8")
    assert '@app.get("/escenarios"' not in main_source
    assert '@app.post("/escenarios/' not in main_source
    assert "register_scenario_routes(" in main_source
    assert module_source.count("@app.") == 3
    for authority in ("get_scenario", "scenario_summary", "portfolio_macc"):
        assert authority in module_source
    assert '@app.get("/verificacion"' not in module_source


def test_v190_scenario_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in SCENARIO_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == SCENARIO_ROUTES
    assert len(actual) == len(SCENARIO_ROUTES)


def test_v190_scenario_client_is_read_only():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/escenarios")
        assert page.status_code == 200
        denied = client.post(
            "/escenarios/nuevo",
            data={
                "inventory_id": "1",
                "name": "Escenario denegado V1.9",
                "description": "No debe crearse",
                "start_year": "2026",
                "target_year": "2030",
                "discount_rate": "8",
            },
            follow_redirects=False,
        )
        assert denied.status_code == 403
