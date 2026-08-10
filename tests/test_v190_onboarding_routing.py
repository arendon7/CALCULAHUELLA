from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

ONBOARDING_ROUTES = {
    ("GET", "/onboarding"),
    ("POST", "/onboarding/{item_id}/actualizar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_onboarding_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/customer_onboarding_web.py").read_text(encoding="utf-8")
    assert '@app.get("/onboarding"' not in main_source
    assert '@app.post("/onboarding/' not in main_source
    assert "register_customer_onboarding_routes(" in main_source
    assert module_source.count("@app.") == 2
    assert "onboarding_summary" in module_source
    assert "CustomerOnboardingItem.organization_id" in module_source
    assert "_lead_complexity" not in module_source


def test_v190_onboarding_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in ONBOARDING_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == ONBOARDING_ROUTES
    assert len(actual) == len(ONBOARDING_ROUTES)


def test_v190_onboarding_page_remains_available_to_client():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/onboarding")
        assert page.status_code == 200
        assert "Calcula tu Huella" in page.text
