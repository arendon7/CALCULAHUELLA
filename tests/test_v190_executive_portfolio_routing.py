from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_v190_executive_portfolio_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/executive_portfolio_web.py").read_text(encoding="utf-8")
    assert '@app.get("/direccion-ejecutiva"' not in main_source
    assert "register_executive_portfolio_routes(" in main_source
    assert module_source.count("@app.") == 1
    assert "from .compliance_web import compliance_score" in module_source
    assert "_compliance_score" not in module_source
    assert "OrganizationMembership" in module_source
    assert '@app.get("/cumplimiento"' not in module_source


def test_v190_executive_portfolio_route_contract_is_unique():
    actual = []
    for route in app.routes:
        if getattr(route, "path", None) == "/direccion-ejecutiva":
            actual.extend(method for method in (getattr(route, "methods", set()) or set()) if method == "GET")
    assert actual == ["GET"]


def test_v190_executive_portfolio_access_remains_capability_bound():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/direccion-ejecutiva").status_code == 403
        client.post("/logout")
        _login(client, "consultor@calculatuhuella.local")
        assert client.get("/direccion-ejecutiva").status_code == 200
