from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

COMMERCIAL_OPERATIONS_ROUTES = {
    ("GET", "/operacion-comercial"),
    ("POST", "/operacion-comercial/contratos/nuevo"),
    ("POST", "/operacion-comercial/contratos/{contract_id}/firmar"),
    ("POST", "/operacion-comercial/contratos/{contract_id}/estado"),
    ("POST", "/operacion-comercial/contratos/{contract_id}/renovar"),
    ("POST", "/operacion-comercial/ordenes/nueva"),
    ("POST", "/operacion-comercial/ordenes/{order_id}/estado"),
    ("POST", "/operacion-comercial/cobros/recurrente"),
    ("POST", "/operacion-comercial/cartera/nueva"),
    ("POST", "/operacion-comercial/cartera/{action_id}/completar"),
    ("POST", "/operacion-comercial/documentos/{document_id}/actualizar"),
}


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v170_commercial_operations_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/commercial_operations_web.py").read_text(encoding="utf-8")
    assert '@app.get("/operacion-comercial"' not in main_source
    assert '@app.post("/operacion-comercial/' not in main_source
    assert "register_commercial_operations_routes(" in main_source
    assert module_source.count("@app.") == 11
    assert "def _contract_signature_hash" in module_source
    assert "def _contract_reference" in module_source
    assert "def _order_reference" in module_source
    assert "def _require_customer_success_view" not in module_source


def test_v170_commercial_operations_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in COMMERCIAL_OPERATIONS_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == COMMERCIAL_OPERATIONS_ROUTES
    assert len(actual) == len(COMMERCIAL_OPERATIONS_ROUTES)


def test_v170_commercial_operations_page_remains_available():
    with TestClient(app) as client:
        _login(client)
        response = client.get("/operacion-comercial")
        assert response.status_code == 200
        assert "Calcula tu Huella" in response.text
