from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CLIMATE_RISK_ROUTES = {
    ("GET", "/riesgos-climaticos"),
    ("POST", "/riesgos-climaticos/evaluacion"),
    ("POST", "/riesgos-climaticos/riesgos/nuevo"),
    ("POST", "/riesgos-climaticos/riesgos/{risk_id}/actualizar"),
    ("POST", "/riesgos-climaticos/controles/nuevo"),
    ("POST", "/riesgos-climaticos/hoja-ruta"),
    ("POST", "/riesgos-climaticos/acciones/nueva"),
    ("POST", "/riesgos-climaticos/acciones/{action_id}/estado"),
    ("GET", "/riesgos-climaticos/exportar.xlsx"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v180_climate_risk_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/climate_risk_web.py").read_text(encoding="utf-8")
    assert '@app.get("/riesgos-climaticos"' not in main_source
    assert '@app.post("/riesgos-climaticos/' not in main_source
    assert "register_climate_risk_routes(" in main_source
    assert module_source.count("@app.") == 9
    assert "def _require_climate_risk_view" in module_source
    assert "def _require_climate_disclosure_view" not in module_source
    for authority in (
        "assessment_summary",
        "calculate_risk_scores",
        "risk_level",
        "synchronize_control_effectiveness",
        "refresh_assessment_status",
    ):
        assert authority in module_source


def test_v180_climate_risk_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in CLIMATE_RISK_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == CLIMATE_RISK_ROUTES
    assert len(actual) == len(CLIMATE_RISK_ROUTES)


def test_v180_climate_risk_client_stays_read_only():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/riesgos-climaticos")
        assert page.status_code == 200
        denied = client.post(
            "/riesgos-climaticos/riesgos/nuevo",
            data={
                "risk_type": "Físico",
                "category": "Agudo",
                "hazard": "Prueba V1.8 denegada",
                "owner": "Operaciones",
                "likelihood": "3",
                "financial_impact": "3",
                "operational_impact": "3",
                "reputational_impact": "2",
            },
            follow_redirects=False,
        )
        assert denied.status_code == 403
