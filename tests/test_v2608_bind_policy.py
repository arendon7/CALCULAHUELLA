from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from app.db.models import BillingInvoice, CommercialProposal, OrganizationSubscription, ServiceContract


def _bound(model, column_name: str, value: object, dialect) -> Decimal:
    column_type = model.__table__.c[column_name].type
    processor = column_type.bind_processor(dialect)
    processed = processor(value) if processor is not None else value
    return Decimal(str(processed))


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v2608_money_bind_policy_is_round_half_up_on_supported_dialects(dialect) -> None:
    assert _bound(ServiceContract, "contract_value", Decimal("100.005"), dialect) == Decimal("100.01")
    assert _bound(BillingInvoice, "amount", Decimal("12.344"), dialect) == Decimal("12.34")
    assert _bound(CommercialProposal, "tax_rate", Decimal("19.12345"), dialect) == Decimal("19.1235")
    assert _bound(
        OrganizationSubscription,
        "custom_monthly_fee",
        Decimal("1.2345675"),
        dialect,
    ) == Decimal("1.234568")


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_v2608_economic_bind_policy_fails_closed_for_non_finite_values(bad: Decimal) -> None:
    column_type = ServiceContract.__table__.c.contract_value.type
    processor = column_type.bind_processor(postgresql.dialect())
    assert processor is not None
    with pytest.raises(ValueError):
        processor(bad)
