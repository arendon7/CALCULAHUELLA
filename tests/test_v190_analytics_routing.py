from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

ANALYTICS_ROUTES = {
    ("GET", "/analisis"),
    ("GET", "/inventarios/{inventory_id}/analisis"),
    ("POST", "/analisis/indicadores/nuevo"),
    ("POST", "/analisis/indicadores/{indicator_id}/editar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_analytics_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/analytics_web.py").read_text(encoding="utf-8")
    assert '@app.get("/analisis"' not in main_source
    assert '@app.post("/analisis/indicadores/' not in main_source
    assert "register_analytics_routes(" in main_source
    assert module_source.count("@app.") == 4
    assert '@app.get("/inventarios/{inventory_id}/analisis"' in module_source
    assert "full_analysis" in module_source
    assert "ActivityIndicator" in module_source
    assert "_parse_excel_period" not in module_source
    assert '@app.get("/escenarios"' not in module_source


def test_v190_analytics_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in ANALYTICS_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == ANALYTICS_ROUTES
    assert len(actual) == len(ANALYTICS_ROUTES)


def test_v190_analytics_client_can_read_but_not_mutate():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/analisis")
        assert page.status_code == 200
        denied = client.post(
            "/analisis/indicadores/nuevo",
            data={
                "inventory_id": "1",
                "indicator_type": "Producción",
                "value": "10",
                "unit": "t",
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "source_name": "Prueba V1.9",
            },
            follow_redirects=False,
        )
        assert denied.status_code == 403
