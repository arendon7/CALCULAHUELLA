from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_ROUTES = {
    ("POST", "/preferencias/vista"),
    ("GET", "/recorrido-inventario"),
    ("GET", "/dashboard"),
}


def _login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_v190_dashboard_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/dashboard_web.py").read_text(encoding="utf-8")
    for marker in (
        '@app.post("/preferencias/vista"',
        '@app.get("/recorrido-inventario"',
        '@app.get("/dashboard"',
    ):
        assert marker not in main_source
    assert "register_dashboard_routes(" in main_source
    assert module_source.count("@app.") == 3
    for authority in (
        "guided_workspace", "professional_delivery_summary", "onboarding_summary",
        "guided_decision_plan", "normalize_view_mode",
    ):
        assert authority in module_source
    assert "def _parse_excel_period" not in module_source
    for system_route in ('@app.get("/modulos"', '@app.get("/api/health"', '@app.get("/api/ready"'):
        assert system_route in main_source


def test_v190_dashboard_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in DASHBOARD_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == DASHBOARD_ROUTES
    assert len(actual) == len(DASHBOARD_ROUTES)


def test_v190_view_preference_preserves_safe_return_url_contract():
    with TestClient(app) as client:
        _login(client)
        rejected = client.post(
            "/preferencias/vista",
            data={"mode": "essential", "return_url": "//evil.example"},
            follow_redirects=False,
        )
        assert rejected.status_code == 303
        assert rejected.headers["location"] == "/dashboard"
        allowed = client.post(
            "/preferencias/vista",
            data={"mode": "full", "return_url": "/recorrido-inventario"},
            follow_redirects=False,
        )
        assert allowed.status_code == 303
        assert allowed.headers["location"] == "/recorrido-inventario"


def test_v190_dashboard_and_journey_remain_available_to_client():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/dashboard").status_code == 200
        assert client.get("/recorrido-inventario").status_code == 200
