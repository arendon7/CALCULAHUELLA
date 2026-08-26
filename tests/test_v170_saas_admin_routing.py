from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import BillingInvoice, OrganizationSubscription, ServicePlan, SessionLocal
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

SAAS_ROUTES = {
    ("GET", "/administracion-saas"),
    ("POST", "/administracion-saas/planes/nuevo"),
    ("POST", "/administracion-saas/suscripciones/{subscription_id}/actualizar"),
    ("POST", "/administracion-saas/facturas/{invoice_id}/estado"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v170_saas_admin_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/saas_admin_web.py").read_text(encoding="utf-8")
    assert '@app.get("/administracion-saas"' not in main_source
    assert '@app.post("/administracion-saas/' not in main_source
    assert "register_saas_admin_routes(" in main_source
    assert module_source.count("@app.") == 4
    assert "manage_saas" in module_source
    assert "_lead_complexity" not in module_source


def test_v170_saas_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in SAAS_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == SAAS_ROUTES
    assert len(actual) == len(SAAS_ROUTES)


def test_v170_saas_admin_permissions_remain_restricted():
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        response = client.get("/administracion-saas")
        assert response.status_code == 403


def test_v170_saas_subscription_and_invoice_updates_remain_persistent():
    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).order_by(OrganizationSubscription.id))
        assert subscription is not None
        plan = session.scalar(select(ServicePlan).where(ServicePlan.id != subscription.plan_id).order_by(ServicePlan.id))
        if plan is None:
            plan = session.get(ServicePlan, subscription.plan_id)
        assert plan is not None

        # V2.60.12 intentionally forbids declaring an invoice paid when the
        # persisted record only contains a pre-tax base or legacy-unknown
        # semantics. This V1.7 routing test therefore owns an invoice whose
        # full economic total is authoritative instead of depending on the
        # arbitrary first seeded invoice.
        invoice = BillingInvoice(
            organization_id=subscription.organization_id,
            subscription_id=subscription.id,
            reference="INV-V170-TOTAL-KNOWN",
            period_start=date(2027, 1, 1),
            period_end=date(2027, 1, 31),
            amount=119000,
            status="Pendiente",
            issued_at=date(2027, 1, 1),
            due_date=date(2027, 1, 15),
            charge_type="Prueba de routing",
            amount_semantics="total_with_tax",
            net_amount=100000,
            tax_rate_snapshot=19,
            tax_amount=19000,
            total_amount=119000,
            source_reference="V170-ROUTING",
            classification_note="Total de prueba autoritativo para validar persistencia del routing SaaS.",
        )
        session.add(invoice)
        session.commit()
        subscription_id, plan_id, invoice_id = subscription.id, plan.id, invoice.id

    with TestClient(app) as client:
        _login(client, "admin@calculatuhuella.local")
        updated = client.post(
            f"/administracion-saas/suscripciones/{subscription_id}/actualizar",
            data={
                "plan_id": str(plan_id),
                "status": "Activa",
                "billing_cycle": "Mensual",
                "custom_monthly_fee": "123456",
                "renewal_date": "2027-01-15",
                "notes": "Prueba V1.7",
            },
            follow_redirects=False,
        )
        assert updated.status_code == 303
        paid = client.post(
            f"/administracion-saas/facturas/{invoice_id}/estado",
            data={"status": "Pagada"},
            follow_redirects=False,
        )
        assert paid.status_code == 303

    with SessionLocal() as session:
        subscription = session.get(OrganizationSubscription, subscription_id)
        invoice = session.get(BillingInvoice, invoice_id)
        assert subscription.plan_id == plan_id
        assert subscription.status == "Activa"
        assert subscription.billing_cycle == "Mensual"
        assert subscription.custom_monthly_fee == 123456
        assert subscription.renewal_date.isoformat() == "2027-01-15"
        assert invoice.status == "Pagada"
        assert invoice.paid_at is not None
