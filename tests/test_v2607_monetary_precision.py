from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Float, Numeric, func, select

from app.commercial_pricing import (
    proposal_first_year_total,
    proposal_initial_payment,
    subscription_custom_monthly_fee,
)
from app.db.base import SessionLocal
from app.db.models import (
    BillingInvoice,
    CommercialLead,
    CommercialProposal,
    CustomerSuccessProfile,
    OrganizationSubscription,
    PaymentTransaction,
    RenewalOpportunity,
    ServiceContract,
    ServicePlan,
    UsageCounter,
    ValueMilestone,
)
from app.main import app
from app.money import (
    money_equal,
    parse_money,
    parse_rate,
    parse_recurring_basis,
    quantize_money,
)
from app.revenue_operations import activation_breakdown


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "versions" / "20260824_0042_v2607_monetary_precision.py"
COMMERCIAL_MODEL = ROOT / "app" / "db" / "models" / "commercial.py"
SAAS_SOURCE = ROOT / "app" / "saas_admin_web.py"
PAYMENT_SOURCE = ROOT / "app" / "payment_web.py"
OPERATIONS_SOURCE = ROOT / "app" / "commercial_operations_web.py"


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _lead_and_plan() -> tuple[int, int]:
    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).order_by(CommercialLead.id))
        plan = session.scalar(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.id))
        assert lead is not None and plan is not None
        return lead.id, plan.id


def _proposal_payload(title: str) -> dict[str, str]:
    lead_id, plan_id = _lead_and_plan()
    return {
        "lead_id": str(lead_id),
        "plan_id": str(plan_id),
        "title": title,
        "implementation_fee": "1000000.10",
        "recurring_fee": "200000.20",
        "discount_amount": "100000.30",
        "tax_rate": "19.1250",
        "billing_cycle": "Mensual",
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
        "scope": "Alcances 1 y 2",
        "deliverables": "Inventario corporativo",
        "terms": "Condiciones explícitas. Verificación independiente no incluida.",
    }


def _assert_numeric(column, precision: int, scale: int) -> None:
    assert isinstance(column.type, Numeric)
    assert column.type.asdecimal is True
    assert column.type.precision == precision
    assert column.type.scale == scale


def test_v2607_authoritative_money_is_numeric_but_environmental_and_generic_metrics_stay_float() -> None:
    money_columns = [
        ServicePlan.__table__.c.monthly_fee,
        ServicePlan.__table__.c.annual_fee,
        BillingInvoice.__table__.c.amount,
        CommercialProposal.__table__.c.implementation_fee,
        CommercialProposal.__table__.c.recurring_fee,
        CommercialProposal.__table__.c.discount_amount,
        CommercialProposal.__table__.c.first_year_total,
        PaymentTransaction.__table__.c.amount,
        ServiceContract.__table__.c.contract_value,
        RenewalOpportunity.__table__.c.forecast_amount,
        BillingInvoice.__table__.c.net_amount,
        BillingInvoice.__table__.c.tax_amount,
        BillingInvoice.__table__.c.total_amount,
    ]
    for column in money_columns:
        _assert_numeric(column, 18, 2)

    _assert_numeric(CommercialProposal.__table__.c.tax_rate, 9, 6)
    _assert_numeric(BillingInvoice.__table__.c.tax_rate_snapshot, 9, 6)
    _assert_numeric(OrganizationSubscription.__table__.c.custom_monthly_fee, 18, 6)

    assert isinstance(UsageCounter.__table__.c.value.type, Float)
    assert isinstance(CustomerSuccessProfile.__table__.c.satisfaction_score.type, Float)
    assert isinstance(ValueMilestone.__table__.c.expected_value.type, Float)
    assert isinstance(ValueMilestone.__table__.c.realized_value.type, Float)


def test_v2607_decimal_parsers_reject_silent_rounding_and_preserve_contract_hash_precision() -> None:
    assert parse_money("10.10", "el importe") == Decimal("10.10")
    assert parse_rate("19.1250", "la tasa") == Decimal("19.1250")
    assert parse_recurring_basis("8.333333", "la base") == Decimal("8.333333")

    with pytest.raises(ValueError, match="máximo 2 decimales"):
        parse_money("10.101", "el importe")
    with pytest.raises(ValueError, match="máximo 4 decimales"):
        parse_rate("19.12501", "la tasa")
    with pytest.raises(ValueError, match="máximo 6 decimales"):
        parse_recurring_basis("8.3333333", "la base")
    for bad in ("NaN", "Infinity", "-0.01"):
        with pytest.raises(ValueError):
            parse_money(bad, "el importe")


def test_v2607_pricing_uses_decimal_half_up_and_keeps_annual_monthly_basis_subcent_precision() -> None:
    assert proposal_first_year_total(
        Decimal("1000000.00"), Decimal("200000.00"), Decimal("100000.00"), Decimal("19.0000"), "Mensual"
    ) == Decimal("3927000.00")
    assert proposal_initial_payment(
        Decimal("100.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.0050")
    ) == Decimal("100.01")

    monthly_basis = subscription_custom_monthly_fee(Decimal("1200001.00"), "Anual")
    assert monthly_basis == Decimal("100000.083333")
    assert quantize_money(monthly_basis * Decimal("12")) == Decimal("1200001.00")

    parts = activation_breakdown(
        Decimal("1000.10"), Decimal("200.20"), Decimal("100.30"), Decimal("19.1250")
    )
    assert parts == {
        "net_amount": Decimal("1100.00"),
        "tax_rate_snapshot": Decimal("19.125000"),
        "tax_amount": Decimal("210.38"),
        "total_amount": Decimal("1310.38"),
    }
    assert money_equal(parts["total_amount"], Decimal("1310.380"))


def test_v2607_proposal_rejects_excess_money_or_rate_precision_without_persistence() -> None:
    cases = [
        ("implementation_fee", "1000000.101", "máximo 2 decimales"),
        ("tax_rate", "19.12501", "máximo 4 decimales"),
    ]
    for field, bad_value, message in cases:
        title = f"V2.60.7 precision reject {field}"
        payload = _proposal_payload(title)
        payload[field] = bad_value
        with TestClient(app) as client:
            _login(client)
            response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)
        assert response.status_code == 400
        assert message in response.text
        with SessionLocal() as session:
            count = session.scalar(
                select(func.count()).select_from(CommercialProposal).where(CommercialProposal.title == title)
            ) or 0
            assert int(count) == 0


def test_v2607_valid_proposal_round_trips_decimal_economics() -> None:
    title = "V2.60.7 decimal proposal roundtrip"
    payload = _proposal_payload(title)
    expected = proposal_first_year_total(
        Decimal(payload["implementation_fee"]),
        Decimal(payload["recurring_fee"]),
        Decimal(payload["discount_amount"]),
        Decimal(payload["tax_rate"]),
        payload["billing_cycle"],
    )
    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)
    assert response.status_code == 303

    with SessionLocal() as session:
        proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.title == title))
        assert proposal is not None
        assert proposal.implementation_fee == Decimal("1000000.10")
        assert proposal.recurring_fee == Decimal("200000.20")
        assert proposal.discount_amount == Decimal("100000.30")
        assert proposal.tax_rate == Decimal("19.125000")
        assert proposal.first_year_total == expected
        assert all(
            isinstance(value, Decimal)
            for value in (
                proposal.implementation_fee,
                proposal.recurring_fee,
                proposal.discount_amount,
                proposal.tax_rate,
                proposal.first_year_total,
            )
        )


def test_v2607_saas_admin_has_no_float_or_negative_money_coercion() -> None:
    source = SAAS_SOURCE.read_text(encoding="utf-8")
    assert "monthly_fee: float" not in source
    assert "annual_fee: float" not in source
    assert "float(custom_monthly_fee)" not in source
    assert "max(0, monthly_fee)" not in source
    assert "max(0, annual_fee)" not in source
    assert "parse_money" in source
    assert "parse_recurring_basis" in source

    with TestClient(app) as client:
        _login(client)
        response = client.post(
            "/administracion-saas/planes/nuevo",
            data={
                "code": "V2607BAD",
                "name": "V2607 bad precision",
                "description": "",
                "monthly_fee": "10.001",
                "annual_fee": "100.00",
                "max_users": "5",
                "max_facilities": "3",
                "max_inventories": "3",
                "max_storage_mb": "1024",
            },
            follow_redirects=False,
        )
    assert response.status_code == 400
    with SessionLocal() as session:
        assert session.scalar(select(ServicePlan).where(ServicePlan.code == "V2607BAD")) is None


def test_v2607_payment_and_operations_do_not_compare_authoritative_money_as_float() -> None:
    payment_source = PAYMENT_SOURCE.read_text(encoding="utf-8")
    operations_source = OPERATIONS_SOURCE.read_text(encoding="utf-8")

    assert "amount: Decimal" in payment_source
    assert "money_equal(payment.amount, reported_amount)" in payment_source
    assert "abs(payment.amount - payload.amount)" not in payment_source
    assert "abs(float(invoice.amount)" not in payment_source
    assert 'payload.model_dump(mode="json")' in payment_source

    assert "parse_money(contract_value" in operations_source
    assert "parse_money(contract_value, \"el valor de renovación\")" in operations_source
    assert "quantize_money(base_value)" in operations_source
    assert "parse_nonnegative_number(raw_amount" not in operations_source


def test_v2607_migration_is_representation_only_and_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    model_source = COMMERCIAL_MODEL.read_text(encoding="utf-8")

    assert 'revision = "20260824_0042"' in source
    assert 'down_revision = "20260824_0041"' in source
    assert "sa.Numeric(18, 2" in source
    assert "sa.Numeric(9, 6" in source
    assert "sa.Numeric(18, 6" in source
    assert "batch_alter_table" in source
    assert "def downgrade()" in source
    assert "create_table" not in source
    assert "UPDATE " not in source.upper()
    assert "op.execute" not in source

    assert "monthly_fee: Mapped[Decimal]" in model_source
    assert "custom_monthly_fee: Mapped[Decimal | None]" in model_source
    assert "tax_rate: Mapped[Decimal]" in model_source
    assert "value: Mapped[float] = mapped_column(Float" in model_source
