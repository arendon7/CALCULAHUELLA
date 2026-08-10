from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_ROUTES = {
    ("GET", "/mi-trabajo"),
    ("POST", "/mi-trabajo/nueva"),
    ("POST", "/mi-trabajo/sincronizar"),
    ("POST", "/mi-trabajo/{work_item_id}/accion"),
    ("GET", "/api/mi-trabajo"),
}


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_workflow_routes_have_dedicated_http_authority():
    experience = (ROOT / "app/experience_web.py").read_text(encoding="utf-8")
    workflow = (ROOT / "app/workflow_web.py").read_text(encoding="utf-8")
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")

    # La guía conserva legítimamente un enlace hacia Mi trabajo; lo que se
    # separa es la autoridad HTTP y sus dependencias de dominio/servicio.
    assert '@app.get("/mi-trabajo"' not in experience
    assert '@app.post("/mi-trabajo' not in experience
    assert '@app.get("/api/mi-trabajo"' not in experience
    assert "workflow_service" not in experience
    assert "workflow_bridge" not in experience
    assert '"href": "/mi-trabajo"' in experience
    assert workflow.count("@app.") == 5
    assert "register_workflow_routes(" in main
    assert "register_experience_routes(" in main
    assert '@app.get("/guia"' in experience


def test_v160_workflow_route_contract_is_unique_and_complete():
    actual = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path and (path.startswith("/mi-trabajo") or path == "/api/mi-trabajo"):
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == WORKFLOW_ROUTES
    assert len(actual) == len(WORKFLOW_ROUTES)


def test_v160_workflow_and_guide_coexist_after_extraction():
    with TestClient(app) as client:
        _login(client)
        work = client.get("/mi-trabajo?scope=all")
        guide = client.get("/guia")
        api = client.get("/api/mi-trabajo?scope=all")
        assert work.status_code == 200
        assert "Mi trabajo" in work.text
        assert guide.status_code == 200
        assert "Diagnosticar" in guide.text
        assert api.status_code == 200
        assert api.json()["scope"] == "all"
