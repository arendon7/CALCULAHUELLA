from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import OrganizationSubscription, ServicePlan, SessionLocal
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

SERVICE_ACCOUNT_ROUTES = {
    ("GET", "/cuenta-servicio"),
    ("POST", "/cuenta-servicio/suscripcion"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_service_account_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/service_account_web.py").read_text(encoding="utf-8")
    assert '@app.get("/cuenta-servicio"' not in main_source
    assert '@app.post("/cuenta-servicio/' not in main_source
    assert "register_service_account_routes(" in main_source
    assert module_source.count("@app.") == 2
    assert "def _service_usage" in module_source
    assert "UsageCounter" in module_source
    assert '@app.get("/onboarding"' not in module_source


def test_v190_service_account_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in SERVICE_ACCOUNT_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == SERVICE_ACCOUNT_ROUTES
    assert len(actual) == len(SERVICE_ACCOUNT_ROUTES)


def test_v190_service_account_subscription_update_persists_and_client_is_read_only():
    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == 1))
        assert subscription is not None
        plan = session.scalar(select(ServicePlan).where(ServicePlan.active.is_(True), ServicePlan.id != subscription.plan_id).order_by(ServicePlan.id))
        if plan is None:
            plan = session.get(ServicePlan, subscription.plan_id)
        assert plan is not None
        plan_id = plan.id

    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        assert client.get("/cuenta-servicio").status_code == 200
        denied = client.post(
            "/cuenta-servicio/suscripcion",
            data={"plan_id": str(plan_id), "billing_cycle": "Mensual"},
            follow_redirects=False,
        )
        assert denied.status_code == 403
        client.post("/logout")
        _login(client, "admin@calculatuhuella.local")
        updated = client.post(
            "/cuenta-servicio/suscripcion",
            data={"plan_id": str(plan_id), "billing_cycle": "Mensual"},
            follow_redirects=False,
        )
        assert updated.status_code == 303

    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == 1))
        assert subscription.plan_id == plan_id
        assert subscription.billing_cycle == "Mensual"
        assert subscription.status == "Activa"
