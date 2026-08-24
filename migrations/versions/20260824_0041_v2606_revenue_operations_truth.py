"""V2.60.6: verdad semántica de Revenue Operations.

Revision ID: 20260824_0041
Revises: 20260812_0040
Create Date: 2026-08-24

La autoridad histórica permanece en ``billing_invoices`` y
``service_contracts``. Esta revisión agrega únicamente columnas nullable y
versionadas a esas tablas: los registros legacy quedan sin clasificación hasta
que exista evidencia suficiente; no se infieren neto, impuesto, total ni un
snapshot contractual retroactivo.

La aplicación histórica creó parte del esquema con ``Base.metadata.create_all``.
Por eso el upgrade inspecciona columna por columna y es deliberadamente
idempotente para SQLite y PostgreSQL.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260824_0041"
down_revision = "20260812_0040"
branch_labels = None
depends_on = None


INVOICE_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("charge_type", sa.String(40)),
    ("amount_semantics", sa.String(40)),
    ("net_amount", sa.Float()),
    ("tax_rate_snapshot", sa.Float()),
    ("tax_amount", sa.Float()),
    ("total_amount", sa.Float()),
    ("source_reference", sa.String(120)),
    ("classification_note", sa.Text()),
    ("semantics_created_at", sa.DateTime()),
)

CONTRACT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("signature_version", sa.String(20)),
    ("signature_payload", sa.Text()),
    ("signature_snapshot_created_at", sa.DateTime()),
)


def _column_names(bind, table_name: str) -> set[str]:
    return {item["name"] for item in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "billing_invoices" in tables:
        invoice_columns = _column_names(bind, "billing_invoices")
        for name, column_type in INVOICE_COLUMNS:
            if name not in invoice_columns:
                op.add_column("billing_invoices", sa.Column(name, column_type, nullable=True))

    if "service_contracts" in tables:
        contract_columns = _column_names(bind, "service_contracts")
        for name, column_type in CONTRACT_COLUMNS:
            if name not in contract_columns:
                op.add_column("service_contracts", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    # No eliminamos automáticamente evidencia contractual ni clasificación de
    # cobro. La precisión monetaria Float -> Numeric/Decimal se abordará en una
    # revisión posterior, una vez estabilizada esta semántica.
    return
