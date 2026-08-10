from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

SUPPORT_ROUTES = {
    ("GET", "/soporte"),
    ("GET", "/soporte/{ticket_id}"),
    ("POST", "/soporte/nuevo"),
    ("POST", "/soporte/{ticket_id}/mensajes"),
    ("POST", "/soporte/{ticket_id}/actualizar"),
    ("GET", "/api/soporte/resumen"),
}


def _login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v170_support_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/support_web.py").read_text(encoding="utf-8")
    assert '@app.get("/soporte"' not in main_source
    assert '@app.post("/soporte/' not in main_source
    assert '@app.get("/api/soporte/resumen"' not in main_source
    assert "register_support_routes(" in main_source
    assert module_source.count("@app.") == 6
    assert "from .support_workflow import" in module_source
    for name in (
        "support_summary", "route_assignment", "response_deadline",
        "add_support_message", "ticket_context", "ticket_overdue",
    ):
        assert f"def {name}(" not in module_source


def test_v170_support_route_contract_is_unique_and_complete():
    actual = []
    relevant_paths = {path for _, path in SUPPORT_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant_paths:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == SUPPORT_ROUTES
    assert len(actual) == len(SUPPORT_ROUTES)


def test_v170_support_page_and_api_remain_operational():
    with TestClient(app) as client:
        _login(client)
        page = client.get("/soporte")
        summary = client.get("/api/soporte/resumen")
        assert page.status_code == 200
        assert "Centro de conversaciones y requerimientos" in page.text
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["version"] == "1.0.0"
        assert {"open", "critical", "closed", "overdue", "waiting_client", "methodology"} <= set(payload["summary"])
