from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.db.models import BillingInvoice, Organization, OrganizationSubscription, ServiceContract
from app.main import app


def login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v2608_new_contract_rounds_half_up_before_authoritative_persistence() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        organization_id = organization.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion-comercial/contratos/nuevo",
            data={
                "organization_id": organization_id,
                "proposal_id": "",
                "reference": "CTR-V2608-ROUND",
                "title": "Contrato frontera monetaria",
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
                "renewal_type": "Por acuerdo",
                "notice_days": "30",
                "contract_value": "100.005",
                "billing_cycle": "Anual",
                "owner": "Equipo comercial",
                "terms_snapshot": "Prueba de cuantización autoritativa V2.60.8",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as session:
        contract = session.scalar(
            select(ServiceContract).where(ServiceContract.reference == "CTR-V2608-ROUND")
        )
        assert contract is not None
        assert contract.contract_value == Decimal("100.01")


def test_v2608_renewal_rounds_half_up_before_authoritative_persistence() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        original = ServiceContract(
            organization_id=organization.id,
            reference="CTR-V2608-BASE",
            title="Contrato base V2.60.8",
            version="1.0",
            status="Vigente",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 8, 31),
            renewal_type="Anual",
            auto_renew=False,
            notice_days=30,
            contract_value=Decimal("100.00"),
            billing_cycle="Anual",
            owner="Equipo comercial",
            terms_snapshot="Condiciones base",
            created_by="test@calculatuhuella.local",
        )
        session.add(original)
        session.commit()
        original_id = original.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            f"/operacion-comercial/contratos/{original_id}/renovar",
            data={
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
                "contract_value": "100.005",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as session:
        original = session.get(ServiceContract, original_id)
        renewed = session.scalar(
            select(ServiceContract).where(ServiceContract.parent_contract_id == original_id)
        )
        assert original is not None and original.status == "Renovado"
        assert renewed is not None
        assert renewed.contract_value == Decimal("100.01")


def test_v2608_recurring_charge_rounds_normalized_monthly_authority_at_money_boundary() -> None:
    with SessionLocal() as session:
        subscription = session.scalar(
            select(OrganizationSubscription)
            .where(OrganizationSubscription.billing_cycle == "Anual")
            .order_by(OrganizationSubscription.id)
        )
        assert subscription is not None
        subscription.custom_monthly_fee = Decimal("8.333750")
        session.commit()
        subscription_id = subscription.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion-comercial/cobros/recurrente",
            data={
                "subscription_id": subscription_id,
                "period_start": "2026-11-01",
                "period_end": "2026-11-30",
                "due_date": "2026-12-05",
                "reference": "REC-V2608-ROUND",
                "notes": "Prueba de frontera monetaria V2.60.8",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as session:
        invoice = session.scalar(
            select(BillingInvoice).where(BillingInvoice.reference == "REC-V2608-ROUND")
        )
        assert invoice is not None
        assert invoice.amount == Decimal("100.01")
        assert invoice.net_amount == Decimal("100.01")


def test_v2608_scale_policy_is_enforced_for_money_rate_and_normalized_values() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        subscription = session.scalar(select(OrganizationSubscription).order_by(OrganizationSubscription.id))
        assert organization is not None and subscription is not None

        contract = ServiceContract(
            organization_id=organization.id,
            reference="CTR-V2608-SCALE",
            title="Contrato escalas V2.60.8",
            version="1.0",
            status="Borrador",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 8, 31),
            renewal_type="Por acuerdo",
            auto_renew=False,
            notice_days=30,
            contract_value=Decimal("12.345"),
            billing_cycle="Anual",
            owner="Equipo comercial",
            terms_snapshot="Escalas exactas",
            created_by="test@calculatuhuella.local",
        )
        subscription.custom_monthly_fee = Decimal("1.2345675")
        session.add(contract)
        session.commit()
        contract_id = contract.id
        subscription_id = subscription.id

    with SessionLocal() as session:
        contract = session.get(ServiceContract, contract_id)
        subscription = session.get(OrganizationSubscription, subscription_id)
        assert contract is not None and contract.contract_value == Decimal("12.35")
        assert subscription is not None and subscription.custom_monthly_fee == Decimal("1.234568")
