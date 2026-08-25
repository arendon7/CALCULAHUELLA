from __future__ import annotations

from decimal import Decimal

from sqlalchemy import inspect as sa_inspect, select

from app.commercial_web import _parse_nonnegative_number
from app.database import SessionLocal
from app.db.models import CommercialProposal, ServicePlan
from app.db.models.revenue import ExactDecimal
from app.db.monetary_types import money_type, rate_type


def test_v26010_1_normalization_restores_exact_decimal_runtime_semantics() -> None:
    money = money_type().normalize_value(Decimal("100.005"))
    rate = rate_type().normalize_value(Decimal("19.0000"))

    assert isinstance(money, ExactDecimal)
    assert money == Decimal("100.01")
    assert isinstance(rate, ExactDecimal)
    assert rate == Decimal("19.0000")

    # Compatibility with historical arithmetic never routes the float through
    # its binary representation.
    assert money * 1.19 == Decimal("119.0119")

    # Storage scale is preserved, while human-facing :g formatting stays clean.
    assert rate.as_tuple().exponent == -4
    assert f"{rate:g}" == "19"
    assert f"{ExactDecimal('19.1200'):g}" == "19.12"


def test_v26010_1_legacy_commercial_parser_name_delegates_to_exact_money_policy() -> None:
    assert _parse_nonnegative_number("100.005", "el valor") == Decimal("100.01")

    try:
        _parse_nonnegative_number("70368744177664.00", "el valor")
    except ValueError as exc:
        assert "no puede ser mayor" in str(exc)
    else:
        raise AssertionError("El alias de compatibilidad omitió el límite monetario portable")


def test_v26010_1_new_economic_values_are_exact_decimal_after_flush() -> None:
    with SessionLocal() as session:
        plan = ServicePlan(
            code="V260101-RUNTIME",
            name="Runtime decimal hotfix",
            description="Prueba V2.60.10.1",
            monthly_fee=Decimal("100.005"),
            annual_fee=Decimal("1200.005"),
            max_users=1,
            max_facilities=1,
            max_inventories=1,
            max_storage_mb=1,
            active=True,
        )
        session.add(plan)
        session.flush()

        assert isinstance(plan.monthly_fee, ExactDecimal)
        assert isinstance(plan.annual_fee, ExactDecimal)
        assert plan.monthly_fee == Decimal("100.01")
        assert plan.annual_fee == Decimal("1200.01")


def test_v26010_1_loaded_and_refreshed_values_restore_exact_decimal_without_dirtying_row() -> None:
    with SessionLocal() as session:
        proposal_id = session.scalar(select(CommercialProposal.id).order_by(CommercialProposal.id))
        assert proposal_id is not None

    with SessionLocal() as session:
        proposal = session.get(CommercialProposal, proposal_id)
        assert proposal is not None
        assert isinstance(proposal.tax_rate, ExactDecimal)
        assert isinstance(proposal.first_year_total, ExactDecimal)
        assert proposal not in session.dirty

        session.refresh(proposal, attribute_names=["tax_rate", "first_year_total"])
        assert isinstance(proposal.tax_rate, ExactDecimal)
        assert isinstance(proposal.first_year_total, ExactDecimal)
        assert proposal not in session.dirty
        assert not sa_inspect(proposal).attrs.tax_rate.history.has_changes()
        assert not sa_inspect(proposal).attrs.first_year_total.history.has_changes()


def test_v26010_1_demo_seed_keeps_legacy_tax_note_human_readable() -> None:
    with SessionLocal() as session:
        proposal = session.scalar(
            select(CommercialProposal).where(CommercialProposal.reference == "PROP-DEMO-2026-001")
        )
        assert proposal is not None
        assert isinstance(proposal.tax_rate, ExactDecimal)
        assert f"{proposal.tax_rate:g}%" == "19%"
