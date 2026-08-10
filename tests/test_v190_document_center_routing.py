from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

DOCUMENT_ROUTES = {
    ("GET", "/centro-documental"),
    ("POST", "/centro-documental/registros/nuevo"),
    ("POST", "/centro-documental/registros/{record_id}/actualizar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_document_center_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/document_center_web.py").read_text(encoding="utf-8")
    assert '@app.get("/centro-documental"' not in main_source
    assert '@app.post("/centro-documental/' not in main_source
    assert "register_document_center_routes(" in main_source
    assert module_source.count("@app.") == 3
    assert "DocumentControlRecord" in module_source
    assert "EvidenceDocument" in module_source
    assert "ReportArtifact" in module_source
    assert '@app.get("/alistamiento"' not in module_source


def test_v190_document_center_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in DOCUMENT_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == DOCUMENT_ROUTES
    assert len(actual) == len(DOCUMENT_ROUTES)


def test_v190_document_center_remains_permission_bound():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/centro-documental").status_code == 403
        client.post("/logout")
        _login(client, "consultor@calculatuhuella.local")
        assert client.get("/centro-documental").status_code == 200
