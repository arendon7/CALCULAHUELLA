from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

IMPACT_ROUTES = {
    ("GET", "/inteligencia-impacto"),
    ("POST", "/inteligencia-impacto/recalcular"),
    ("POST", "/inteligencia-impacto/benchmarks/nuevo"),
    ("POST", "/inteligencia-impacto/benchmarks/{reference_id}/estado"),
    ("GET", "/inteligencia-impacto/exportar.xlsx"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v180_impact_intelligence_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/impact_intelligence_web.py").read_text(encoding="utf-8")
    assert '@app.get("/inteligencia-impacto"' not in main_source
    assert '@app.post("/inteligencia-impacto/' not in main_source
    assert "register_impact_intelligence_routes(" in main_source
    assert module_source.count("@app.") == 5
    assert "def _require_impact_view" in module_source
    assert "def _require_climate_risk_view" not in module_source
    assert "impact_metrics" in module_source
    assert "refresh_impact_snapshot" in module_source
    assert "compare_benchmarks" in module_source
    assert "portfolio_comparison" in module_source


def test_v180_impact_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in IMPACT_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == IMPACT_ROUTES
    assert len(actual) == len(IMPACT_ROUTES)


def test_v180_impact_client_stays_read_only():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/inteligencia-impacto")
        assert page.status_code == 200
        denied = client.post("/inteligencia-impacto/recalcular", follow_redirects=False)
        assert denied.status_code == 403
