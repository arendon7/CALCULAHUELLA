from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

PORTFOLIO_ROUTES = {
    ("GET", "/portafolio"),
    ("POST", "/portafolio/cambiar/{organization_id}"),
    ("POST", "/portafolio/nueva"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_portfolio_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/portfolio_web.py").read_text(encoding="utf-8")
    assert '@app.get("/portafolio"' not in main_source
    assert '@app.post("/portafolio/' not in main_source
    assert "register_portfolio_routes(" in main_source
    assert module_source.count("@app.") == 3
    assert "OrganizationMembership" in module_source
    assert 'request.session["active_org_id"]' in module_source
    assert "manage_org" in module_source
    assert "_compliance_score" not in module_source


def test_v190_portfolio_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in PORTFOLIO_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == PORTFOLIO_ROUTES
    assert len(actual) == len(PORTFOLIO_ROUTES)


def test_v190_portfolio_read_access_remains_capability_bound():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/portafolio").status_code == 403
        client.post("/logout")
        _login(client, "consultor@calculatuhuella.local")
        assert client.get("/portafolio").status_code == 200
