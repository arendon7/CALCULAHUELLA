from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CONSOLIDATION_ROUTES = {
    ("GET", "/consolidacion"),
    ("POST", "/consolidacion/hallazgos/{finding_id}"),
    ("POST", "/consolidacion/puertas/{gate_id}"),
    ("POST", "/consolidacion/recorridos/{validation_id}"),
    ("GET", "/consolidacion/exportar.xlsx"),
    ("GET", "/api/arquitectura/resumen"),
    ("GET", "/api/consolidacion/resumen"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v180_consolidation_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/consolidation_web.py").read_text(encoding="utf-8")
    for marker in (
        '@app.get("/consolidacion"',
        '@app.post("/consolidacion/',
        '@app.get("/api/arquitectura/resumen"',
        '@app.get("/api/consolidacion/resumen"',
    ):
        assert marker not in main_source
    assert "register_consolidation_routes(" in main_source
    assert module_source.count("@app.") == 7
    assert "consolidation_summary" in module_source
    assert "domain_architecture_summary" in module_source
    assert "ReleaseGate" in module_source
    assert "JourneyValidation" in module_source


def test_v180_consolidation_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in CONSOLIDATION_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == CONSOLIDATION_ROUTES
    assert len(actual) == len(CONSOLIDATION_ROUTES)


def test_v180_consolidation_access_remains_internal():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/consolidacion").status_code == 403
        client.post("/logout")
        _login(client, "verificador@calculatuhuella.local")
        assert client.get("/consolidacion").status_code == 200
