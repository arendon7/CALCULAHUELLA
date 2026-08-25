"""V2.60.7: precisión monetaria determinista.

Revision ID: 20260825_0042
Revises: 20260824_0041
Create Date: 2026-08-25

Convierte únicamente importes económicos autoritativos y tasas contractuales.
Los Float científicos, ambientales, de uso, satisfacción y demás métricas no
monetarias permanecen intactos.

La representación canónica es:
- dinero cobrable/contractual: NUMERIC(20, 2);
- equivalente mensual interno de suscripción: NUMERIC(20, 6);
- tasas tributarias contractuales: NUMERIC(9, 4).

La migración no clasifica filas legacy, no recalcula contratos ni reescribe
payloads/hashes de aceptación o firma. Solo normaliza la representación numérica
al mismo número de decimales que ya forma parte de sus snapshots canónicos.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql.sqltypes import Numeric

revision = "20260825_0042"
down_revision = "20260824_0041"
branch_labels = None
depends_on = None


TARGETS: dict[str, dict[str, tuple[int, int]]] = {
    "service_plans": {
        "monthly_fee": (20, 2),
        "annual_fee": (20, 2),
    },
    "organization_subscriptions": {
        "custom_monthly_fee": (20, 6),
    },
    "billing_invoices": {
        "amount": (20, 2),
        "net_amount": (20, 2),
        "tax_rate_snapshot": (9, 4),
        "tax_amount": (20, 2),
        "total_amount": (20, 2),
    },
    "commercial_proposals": {
        "implementation_fee": (20, 2),
        "recurring_fee": (20, 2),
        "discount_amount": (20, 2),
        "tax_rate": (9, 4),
        "first_year_total": (20, 2),
    },
    "payment_transactions": {
        "amount": (20, 2),
    },
    "service_contracts": {
        "contract_value": (20, 2),
    },
    "renewal_opportunities": {
        "forecast_amount": (20, 2),
    },
}


def _target_type(precision: int, scale: int) -> sa.Numeric:
    return sa.Numeric(precision=precision, scale=scale, asdecimal=True)


def _already_exact(column_type: sa.types.TypeEngine, precision: int, scale: int) -> bool:
    return (
        isinstance(column_type, Numeric)
        and column_type.precision == precision
        and column_type.scale == scale
    )


def _quoted(bind, identifier: str) -> str:
    return bind.dialect.identifier_preparer.quote(identifier)


def _canonicalize_values(bind, table_name: str, columns: dict[str, tuple[int, int]]) -> None:
    table = _quoted(bind, table_name)
    for column_name, (_, scale) in columns.items():
        column = _quoted(bind, column_name)
        if bind.dialect.name == "postgresql":
            bind.execute(sa.text(
                f"UPDATE {table} SET {column} = ROUND(CAST({column} AS numeric), :scale) "
                f"WHERE {column} IS NOT NULL"
            ), {"scale": scale})
        elif bind.dialect.name == "sqlite":
            bind.execute(sa.text(
                f"UPDATE {table} SET {column} = ROUND({column}, :scale) WHERE {column} IS NOT NULL"
            ), {"scale": scale})


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name, targets in TARGETS.items():
        if table_name not in tables:
            continue

        columns = {item["name"]: item for item in inspect(bind).get_columns(table_name)}
        changes = {
            name: spec
            for name, spec in targets.items()
            if name in columns and not _already_exact(columns[name]["type"], *spec)
        }
        if not changes:
            continue

        # Canonicalize the human monetary value before changing physical type.
        # This removes binary-float tails without changing economic semantics.
        _canonicalize_values(bind, table_name, changes)

        if bind.dialect.name == "sqlite":
            # SQLite cannot ALTER COLUMN TYPE. Alembic batch mode recreates only
            # the affected table while preserving its constraints and indexes.
            with op.batch_alter_table(table_name, recreate="always") as batch:
                for name, (precision, scale) in changes.items():
                    batch.alter_column(
                        name,
                        existing_type=columns[name]["type"],
                        type_=_target_type(precision, scale),
                        existing_nullable=columns[name].get("nullable", True),
                    )
        else:
            for name, (precision, scale) in changes.items():
                quoted = _quoted(bind, name)
                kwargs = {
                    "existing_type": columns[name]["type"],
                    "type_": _target_type(precision, scale),
                    "existing_nullable": columns[name].get("nullable", True),
                }
                if bind.dialect.name == "postgresql":
                    kwargs["postgresql_using"] = (
                        f"ROUND(CAST({quoted} AS numeric), {scale})"
                    )
                op.alter_column(table_name, name, **kwargs)


def downgrade() -> None:
    # Deliberadamente no degradamos de Numeric/Decimal a Float. Hacerlo volvería
    # a introducir pérdida binaria sobre evidencia económica ya persistida.
    return
