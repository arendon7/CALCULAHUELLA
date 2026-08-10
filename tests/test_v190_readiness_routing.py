from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

READINESS_ROUTES = {
    ("GET", "/alistamiento"),
    ("POST", "/alistamiento/{item_id}/actualizar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_readiness_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/readiness_web.py").read_text(encoding="utf-8")
    assert '@app.get("/alistamiento"' not in main_source
    assert '@app.post("/alistamiento/' not in main_source
    assert "register_readiness_routes(" in main_source
    assert module_source.count("@app.") == 2
    assert "CommercialReadinessItem" in module_source
    assert "manage_readiness" in module_source
    assert "_lead_complexity" not in module_source


def test_v190_readiness_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in READINESS_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == READINESS_ROUTES
    assert len(actual) == len(READINESS_ROUTES)


def test_v190_readiness_remains_admin_restricted():
    with TestClient(app) as client:
        _login(client, "consultor@calculatuhuella.local")
        assert client.get("/alistamiento").status_code == 403
        client.post("/logout")
        _login(client, "admin@calculatuhuella.local")
        assert client.get("/alistamiento").status_code == 200
