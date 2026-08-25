from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.sql.sqltypes import Float, Numeric

from app.commercial_pricing import (
    proposal_first_year_total,
    proposal_initial_payment,
    recurring_first_year_value,
    subscription_custom_monthly_fee,
)
from app.db.models import (
    BillingInvoice,
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
from app.db.models.revenue import ExactDecimal
from app.monetary import (
    parse_nonnegative_money,
    parse_nonnegative_rate,
    quantize_money,
)
from app.revenue_operations import activation_breakdown, contract_signature_hash, contract_signature_source


def _column_type(model, name: str):
    return model.__table__.c[name].type


def _assert_numeric(model, name: str, precision: int, scale: int) -> None:
    column_type = _column_type(model, name)
    assert isinstance(column_type, Numeric), (model.__name__, name, column_type)
    assert column_type.precision == precision
    assert column_type.scale == scale
    assert column_type.asdecimal is True


def test_v2607_authoritative_money_uses_exact_numeric_and_scientific_float_stays_float() -> None:
    money_columns = {
        ServicePlan: ("monthly_fee", "annual_fee"),
        BillingInvoice: ("amount", "net_amount", "tax_amount", "total_amount"),
        CommercialProposal: (
            "implementation_fee",
            "recurring_fee",
            "discount_amount",
            "first_year_total",
        ),
        PaymentTransaction: ("amount",),
        ServiceContract: ("contract_value",),
        RenewalOpportunity: ("forecast_amount",),
    }
    for model, columns in money_columns.items():
        for column in columns:
            _assert_numeric(model, column, 20, 2)

    _assert_numeric(OrganizationSubscription, "custom_monthly_fee", 20, 6)
    _assert_numeric(CommercialProposal, "tax_rate", 9, 4)
    _assert_numeric(BillingInvoice, "tax_rate_snapshot", 9, 4)

    # Explicit scope lock: V2.60.7 must not decimalize non-economic science or KPIs.
    assert isinstance(_column_type(UsageCounter, "value"), Float)
    assert isinstance(_column_type(CustomerSuccessProfile, "satisfaction_score"), Float)
    assert isinstance(_column_type(ValueMilestone, "expected_value"), Float)
    assert isinstance(_column_type(ValueMilestone, "realized_value"), Float)


def test_v2607_round_half_up_is_explicit_at_money_and_rate_boundaries() -> None:
    assert parse_nonnegative_money("0.105", "el valor") == Decimal("0.11")
    assert parse_nonnegative_money("10.104", "el valor") == Decimal("10.10")
    assert parse_nonnegative_rate("19.12345", "la tasa") == Decimal("19.1235")
    assert parse_nonnegative_rate("100", "la tasa") == Decimal("100.0000")

    with pytest.raises(ValueError):
        parse_nonnegative_money("NaN", "el valor")
    with pytest.raises(ValueError):
        parse_nonnegative_rate("100.0001", "la tasa")


def test_v2607_decimal_pricing_has_no_binary_float_artifacts() -> None:
    assert proposal_initial_payment("0.10", "0.20", "0", "19") == Decimal("0.36")
    assert recurring_first_year_value("0.10", "Mensual") == Decimal("1.20")
    assert proposal_first_year_total("0.10", "0.20", "0", "19", "Mensual") == Decimal("2.98")

    parts = activation_breakdown("100.10", "50.20", "0.30", "19.12345")
    assert parts == {
        "net_amount": Decimal("150.00"),
        "tax_rate_snapshot": Decimal("19.1235"),
        "tax_amount": Decimal("28.69"),
        "total_amount": Decimal("178.69"),
    }


def test_v2607_persisted_decimal_absorbs_legacy_float_literals_without_ieee_artifacts() -> None:
    recurring = ExactDecimal("9900000.00")
    total = (8_500_000 + recurring) * 1.19
    assert isinstance(total, ExactDecimal)
    assert total == Decimal("21896000.0000")
    assert round(total, 2) == Decimal("21896000.00")


def test_v2607_annual_monthly_equivalent_round_trip_preserves_negotiated_cents() -> None:
    monthly_equivalent = subscription_custom_monthly_fee("100.01", "Anual")
    assert monthly_equivalent == Decimal("8.334167")
    assert quantize_money(monthly_equivalent * Decimal("12")) == Decimal("100.01")

    monthly_contract = subscription_custom_monthly_fee("100.01", "Mensual")
    assert monthly_contract == Decimal("100.010000")


def test_v2607_contract_signature_canonical_source_stays_compatible_with_v2606_value_format() -> None:
    signed_at = datetime(2026, 8, 25, 15, 0, tzinfo=UTC)
    base = dict(
        reference="CTR-2026-0001",
        organization_id=7,
        proposal_id=3,
        parent_contract_id=None,
        title="Contrato",
        version="1.0",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 8, 31),
        renewal_type="Anual",
        auto_renew=False,
        notice_days=30,
        billing_cycle="Anual",
        owner="Equipo comercial",
        terms_snapshot="Términos",
    )
    legacy_float = SimpleNamespace(**base, contract_value=1234.5)
    exact_decimal = SimpleNamespace(**base, contract_value=Decimal("1234.50"))

    legacy_source = contract_signature_source(legacy_float, "Firma", "FIRMA@EXAMPLE.COM", signed_at)
    exact_source = contract_signature_source(exact_decimal, "Firma", "FIRMA@EXAMPLE.COM", signed_at)
    assert legacy_source == exact_source
    assert contract_signature_hash(legacy_float, "Firma", "FIRMA@EXAMPLE.COM", signed_at) == contract_signature_hash(
        exact_decimal, "Firma", "FIRMA@EXAMPLE.COM", signed_at
    )
