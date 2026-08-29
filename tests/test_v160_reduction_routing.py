from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

REDUCTION_ROUTES = {
    ("POST", "/reduccion/metas/nueva"),
    ("POST", "/reduccion/metas/{target_id}/actualizar"),
    ("POST", "/reduccion/metas/{target_id}/sincronizar"),
    ("POST", "/reduccion/acciones/nueva"),
    ("POST", "/reduccion/acciones/{action_id}/actualizar"),
    ("GET", "/reduccion"),
    ("GET", "/api/reduccion/resumen"),
    ("GET", "/reduccion/exportar.xlsx"),
}
SCOPED_REDUCTION_ROUTE = ("GET", "/inventarios/{inventory_id}/reduccion")


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_reduction_routes_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/reduction_web.py").read_text(encoding="utf-8")
    assert '@app.get("/reduccion"' not in main_source
    assert '@app.post("/reduccion/' not in main_source
    assert 'register_reduction_routes(' in main_source
    assert module_source.count("@app.") == 9
    assert '@app.get("/inventarios/{inventory_id}/reduccion"' in module_source
    assert "portfolio_summary" in module_source
    assert "from .reporting" not in module_source


def test_v160_reduction_route_contract_is_unique_and_complete():
    actual = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path and (path.startswith("/reduccion") or path.startswith("/api/reduccion")):
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == REDUCTION_ROUTES
    assert len(actual) == len(REDUCTION_ROUTES)

    scoped = [
        (method, getattr(route, "path", None))
        for route in app.routes
        for method in (getattr(route, "methods", set()) or set())
        if method == "GET" and getattr(route, "path", None) == SCOPED_REDUCTION_ROUTE[1]
    ]
    assert scoped == [SCOPED_REDUCTION_ROUTE]


def test_v160_reporting_and_reduction_surfaces_coexist_after_extraction():
    with TestClient(app) as client:
        _login(client)
        assert client.get("/reportes").status_code == 200
        assert client.get("/reportes/consultoria").status_code == 200
        assert client.get("/reduccion").status_code == 200
        assert client.get("/api/reduccion/resumen").status_code == 200
