from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CLIMATE_DISCLOSURE_ROUTES = {
    ("GET", "/divulgacion-climatica"),
    ("POST", "/divulgacion-climatica/escenarios/nuevo"),
    ("POST", "/divulgacion-climatica/escenarios/{scenario_id}/actualizar"),
    ("POST", "/divulgacion-climatica/declaracion"),
    ("POST", "/divulgacion-climatica/requisitos/nuevo"),
    ("POST", "/divulgacion-climatica/requisitos/{requirement_id}/actualizar"),
    ("POST", "/divulgacion-climatica/comite"),
    ("POST", "/divulgacion-climatica/decisiones/nueva"),
    ("POST", "/divulgacion-climatica/decisiones/{decision_id}/estado"),
    ("GET", "/divulgacion-climatica/exportar.xlsx"),
    ("GET", "/divulgacion-climatica/comite.pdf"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v180_climate_disclosure_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/climate_disclosure_web.py").read_text(encoding="utf-8")
    assert '@app.get("/divulgacion-climatica"' not in main_source
    assert '@app.post("/divulgacion-climatica/' not in main_source
    assert "register_climate_disclosure_routes(" in main_source
    assert module_source.count("@app.") == 11
    assert "def _require_climate_disclosure_view" in module_source
    assert '@app.get("/consolidacion"' not in module_source
    for authority in ("scenario_comparison", "disclosure_summary", "board_summary", "build_board_pdf"):
        assert authority in module_source


def test_v180_climate_disclosure_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in CLIMATE_DISCLOSURE_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == CLIMATE_DISCLOSURE_ROUTES
    assert len(actual) == len(CLIMATE_DISCLOSURE_ROUTES)


def test_v180_climate_disclosure_client_stays_read_only():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/divulgacion-climatica")
        assert page.status_code == 200
        denied = client.post(
            "/divulgacion-climatica/escenarios/nuevo",
            data={
                "name": "Escenario denegado V1.8",
                "code": "DEN-V18",
                "scenario_type": "Combinado",
                "physical_multiplier": "1",
                "transition_multiplier": "1",
                "opportunity_multiplier": "1",
                "probability_weight": "0",
            },
            follow_redirects=False,
        )
        assert denied.status_code == 403
