from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from app.database import SessionLocal
from app.db.models import Organization, OrganizationSubscription, ServiceContract, ServicePlan
from app.main import app
from app.monetary import (
    MONEY_PORTABLE_MAX,
    NORMALIZED_MONEY_PORTABLE_MAX,
    RATE_STORAGE_MAX,
    parse_nonnegative_money,
    parse_nonnegative_normalized_money,
)
from app.revenue_operations import parse_nonnegative_number


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _bound(model, column_name: str, value: object, dialect) -> Decimal:
    column_type = model.__table__.c[column_name].type
    processor = column_type.bind_processor(dialect)
    processed = processor(value) if processor is not None else value
    return Decimal(str(processed))


def test_v2609_portable_capacity_constants_are_explicit() -> None:
    assert MONEY_PORTABLE_MAX == Decimal("70368744177663.99")
    assert NORMALIZED_MONEY_PORTABLE_MAX == Decimal("8589934591.999999")
    assert RATE_STORAGE_MAX == Decimal("99999.9999")


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v2609_money_boundary_accepts_last_portable_cent_and_rounds_below_threshold(dialect) -> None:
    assert _bound(ServiceContract, "contract_value", MONEY_PORTABLE_MAX, dialect) == MONEY_PORTABLE_MAX
    assert _bound(
        ServiceContract,
        "contract_value",
        MONEY_PORTABLE_MAX + Decimal("0.004"),
        dialect,
    ) == MONEY_PORTABLE_MAX


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v2609_money_boundary_rejects_first_overflowing_half_cent_and_physical_only_values(dialect) -> None:
    column_type = ServiceContract.__table__.c.contract_value.type
    processor = column_type.bind_processor(dialect)
    assert processor is not None
    with pytest.raises(ValueError, match="límite portable"):
        processor(MONEY_PORTABLE_MAX + Decimal("0.005"))
    with pytest.raises(ValueError, match="límite portable"):
        processor(Decimal("999999999999999999.99"))
    with pytest.raises(ValueError, match="límite portable"):
        processor(Decimal("100000000000000.01"))


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v2609_normalized_money_and_rate_storage_boundaries_are_deterministic(dialect) -> None:
    assert _bound(
        OrganizationSubscription,
        "custom_monthly_fee",
        NORMALIZED_MONEY_PORTABLE_MAX,
        dialect,
    ) == NORMALIZED_MONEY_PORTABLE_MAX

    normalized_type = OrganizationSubscription.__table__.c.custom_monthly_fee.type
    normalized_processor = normalized_type.bind_processor(dialect)
    assert normalized_processor is not None
    with pytest.raises(ValueError, match="límite portable"):
        normalized_processor(NORMALIZED_MONEY_PORTABLE_MAX + Decimal("0.0000005"))

    # ORM storage capacity is distinct from the 0..100 business-input tax rule.
    from app.db.models import CommercialProposal

    assert _bound(CommercialProposal, "tax_rate", RATE_STORAGE_MAX, dialect) == RATE_STORAGE_MAX
    rate_processor = CommercialProposal.__table__.c.tax_rate.type.bind_processor(dialect)
    assert rate_processor is not None
    with pytest.raises(ValueError, match="límite portable"):
        rate_processor(RATE_STORAGE_MAX + Decimal("0.00005"))


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v2609_absurd_magnitudes_fail_as_controlled_value_errors(dialect) -> None:
    processor = ServiceContract.__table__.c.contract_value.type.bind_processor(dialect)
    assert processor is not None
    for raw in (Decimal("1E+1000000"), Decimal("-1E+1000000"), "not-a-number"):
        with pytest.raises(ValueError):
            processor(raw)


def test_v2609_user_parsers_expose_portable_capacity_before_persistence() -> None:
    assert parse_nonnegative_money(str(MONEY_PORTABLE_MAX), "el valor contractual") == MONEY_PORTABLE_MAX
    with pytest.raises(ValueError, match="no puede ser mayor"):
        parse_nonnegative_money(str(MONEY_PORTABLE_MAX + Decimal("0.01")), "el valor contractual")

    assert parse_nonnegative_normalized_money(
        str(NORMALIZED_MONEY_PORTABLE_MAX),
        "la tarifa mensual personalizada",
    ) == NORMALIZED_MONEY_PORTABLE_MAX
    with pytest.raises(ValueError, match="no puede ser mayor"):
        parse_nonnegative_normalized_money(
            str(NORMALIZED_MONEY_PORTABLE_MAX + Decimal("0.000001")),
            "la tarifa mensual personalizada",
        )

    assert parse_nonnegative_number(str(MONEY_PORTABLE_MAX), "el valor contractual") == MONEY_PORTABLE_MAX
    with pytest.raises(ValueError, match="no puede ser mayor"):
        parse_nonnegative_number(str(MONEY_PORTABLE_MAX + Decimal("0.01")), "el valor contractual")


def test_v2609_sqlite_persists_last_portable_cent_exactly() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        contract = ServiceContract(
            organization_id=organization.id,
            reference="CTR-V2609-MAX",
            title="Contrato máximo portable V2.60.9",
            version="1.0",
            status="Borrador",
            start_date=__import__("datetime").date(2026, 9, 1),
            renewal_type="Por acuerdo",
            auto_renew=False,
            notice_days=30,
            contract_value=MONEY_PORTABLE_MAX,
            billing_cycle="Anual",
            owner="CI",
            terms_snapshot="Capacidad portable",
            created_by="ci@calculatuhuella.local",
        )
        session.add(contract)
        session.commit()
        contract_id = contract.id

    with SessionLocal() as session:
        stored = session.get(ServiceContract, contract_id)
        assert stored is not None
        assert stored.contract_value == MONEY_PORTABLE_MAX


def test_v2609_contract_form_rejects_value_beyond_portable_capacity_with_400() -> None:
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
                "reference": "CTR-V2609-OVER",
                "title": "Contrato fuera de capacidad",
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
                "renewal_type": "Por acuerdo",
                "notice_days": "30",
                "contract_value": str(MONEY_PORTABLE_MAX + Decimal("0.01")),
                "billing_cycle": "Anual",
                "owner": "Equipo comercial",
                "terms_snapshot": "Debe fallar antes de persistir",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "no puede ser mayor" in response.text

    with SessionLocal() as session:
        assert session.scalar(
            select(ServiceContract).where(ServiceContract.reference == "CTR-V2609-OVER")
        ) is None


def test_v2609_saas_plan_and_subscription_inputs_reject_nonportable_values_before_commit() -> None:
    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).order_by(OrganizationSubscription.id))
        plan = session.scalar(select(ServicePlan).order_by(ServicePlan.id))
        assert subscription is not None and plan is not None
        subscription_id = subscription.id
        plan_id = plan.id
        previous_custom_fee = subscription.custom_monthly_fee

    with TestClient(app) as client:
        login(client, "admin@calculatuhuella.local")
        plan_response = client.post(
            "/administracion-saas/planes/nuevo",
            data={
                "code": "V2609_OVER",
                "name": "Plan fuera de capacidad",
                "description": "Prueba V2.60.9",
                "monthly_fee": str(MONEY_PORTABLE_MAX + Decimal("0.01")),
                "annual_fee": "0",
                "max_users": "5",
                "max_facilities": "3",
                "max_inventories": "3",
                "max_storage_mb": "1024",
            },
            follow_redirects=False,
        )
        assert plan_response.status_code == 400
        assert "no puede ser mayor" in plan_response.text

        subscription_response = client.post(
            f"/administracion-saas/suscripciones/{subscription_id}/actualizar",
            data={
                "plan_id": plan_id,
                "status": "Activa",
                "billing_cycle": "Anual",
                "custom_monthly_fee": str(NORMALIZED_MONEY_PORTABLE_MAX + Decimal("0.000001")),
                "renewal_date": "",
                "notes": "Debe fallar antes del commit",
            },
            follow_redirects=False,
        )
        assert subscription_response.status_code == 400
        assert "no puede ser mayor" in subscription_response.text

    with SessionLocal() as session:
        assert session.scalar(select(ServicePlan).where(ServicePlan.code == "V2609_OVER")) is None
        subscription = session.get(OrganizationSubscription, subscription_id)
        assert subscription is not None
        assert subscription.custom_monthly_fee == previous_custom_fee
