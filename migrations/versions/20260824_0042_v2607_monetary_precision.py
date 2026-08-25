"""V2.60.7 monetary precision.

Revision ID: 20260824_0042
Revises: 20260824_0041

This revision changes storage representation only. It does not classify legacy
billing rows, recompute accepted proposals, rewrite contractual hashes, or alter
climate/accounting values. Existing binary floats are converted to the declared
fixed-point scale by the database during the type migration.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260824_0042"
down_revision = "20260824_0041"
branch_labels = None
depends_on = None


MONEY = sa.Numeric(18, 2, asdecimal=True)
RATE = sa.Numeric(9, 6, asdecimal=True)
RECURRING_BASIS = sa.Numeric(18, 6, asdecimal=True)
FLOAT = sa.Float()


def _upgrade_table(table: str, columns: list[tuple[str, sa.types.TypeEngine, bool]]) -> None:
    with op.batch_alter_table(table) as batch:
        for name, target_type, nullable in columns:
            batch.alter_column(
                name,
                existing_type=FLOAT,
                type_=target_type,
                existing_nullable=nullable,
            )


def _downgrade_table(table: str, columns: list[tuple[str, sa.types.TypeEngine, bool]]) -> None:
    with op.batch_alter_table(table) as batch:
        for name, source_type, nullable in columns:
            batch.alter_column(
                name,
                existing_type=source_type,
                type_=FLOAT,
                existing_nullable=nullable,
            )


def upgrade() -> None:
    _upgrade_table(
        "service_plans",
        [("monthly_fee", MONEY, False), ("annual_fee", MONEY, False)],
    )
    _upgrade_table(
        "organization_subscriptions",
        [("custom_monthly_fee", RECURRING_BASIS, True)],
    )
    _upgrade_table(
        "billing_invoices",
        [
            ("amount", MONEY, False),
            ("net_amount", MONEY, True),
            ("tax_rate_snapshot", RATE, True),
            ("tax_amount", MONEY, True),
            ("total_amount", MONEY, True),
        ],
    )
    _upgrade_table(
        "commercial_proposals",
        [
            ("implementation_fee", MONEY, False),
            ("recurring_fee", MONEY, False),
            ("discount_amount", MONEY, False),
            ("tax_rate", RATE, False),
            ("first_year_total", MONEY, False),
        ],
    )
    _upgrade_table("payment_transactions", [("amount", MONEY, False)])
    _upgrade_table("service_contracts", [("contract_value", MONEY, False)])
    _upgrade_table("renewal_opportunities", [("forecast_amount", MONEY, False)])


def downgrade() -> None:
    _downgrade_table("renewal_opportunities", [("forecast_amount", MONEY, False)])
    _downgrade_table("service_contracts", [("contract_value", MONEY, False)])
    _downgrade_table("payment_transactions", [("amount", MONEY, False)])
    _downgrade_table(
        "commercial_proposals",
        [
            ("implementation_fee", MONEY, False),
            ("recurring_fee", MONEY, False),
            ("discount_amount", MONEY, False),
            ("tax_rate", RATE, False),
            ("first_year_total", MONEY, False),
        ],
    )
    _downgrade_table(
        "billing_invoices",
        [
            ("amount", MONEY, False),
            ("net_amount", MONEY, True),
            ("tax_rate_snapshot", RATE, True),
            ("tax_amount", MONEY, True),
            ("total_amount", MONEY, True),
        ],
    )
    _downgrade_table("organization_subscriptions", [("custom_monthly_fee", RECURRING_BASIS, True)])
    _downgrade_table(
        "service_plans",
        [("monthly_fee", MONEY, False), ("annual_fee", MONEY, False)],
    )
