from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CUSTOMER_SUCCESS_ROUTES = {
    ("GET", "/exito-cliente"),
    ("POST", "/exito-cliente/perfil"),
    ("POST", "/exito-cliente/salud/recalcular"),
    ("POST", "/exito-cliente/hitos/nuevo"),
    ("POST", "/exito-cliente/hitos/{milestone_id}/estado"),
    ("POST", "/exito-cliente/compromisos/nuevo"),
    ("POST", "/exito-cliente/compromisos/{commitment_id}/estado"),
    ("POST", "/exito-cliente/renovacion/{renewal_id}/actualizar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v170_customer_success_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/customer_success_web.py").read_text(encoding="utf-8")
    assert '@app.get("/exito-cliente"' not in main_source
    assert '@app.post("/exito-cliente/' not in main_source
    assert "register_customer_success_routes(" in main_source
    assert module_source.count("@app.") == 8
    assert "def _require_customer_success_view" in module_source
    assert "def _require_impact_view" not in module_source
    assert "refresh_account_health" in module_source
    assert "sync_renewal_opportunity" in module_source


def test_v170_customer_success_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in CUSTOMER_SUCCESS_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == CUSTOMER_SUCCESS_ROUTES
    assert len(actual) == len(CUSTOMER_SUCCESS_ROUTES)


def test_v170_customer_success_view_and_mutation_permissions_remain_intact():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/exito-cliente")
        assert page.status_code == 200
        assert "Salud y éxito de la cuenta" in page.text
        denied = client.post("/exito-cliente/salud/recalcular", follow_redirects=False)
        assert denied.status_code == 403
