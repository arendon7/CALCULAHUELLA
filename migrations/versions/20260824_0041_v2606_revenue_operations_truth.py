"""V2.60.6: verdad semántica de Revenue Operations.

Revision ID: 20260824_0041
Revises: 20260812_0040
Create Date: 2026-08-24

La aplicación histórica creó varias tablas mediante Base.metadata.create_all(),
por lo que una base nueva puede recibir estas tablas antes de alcanzar esta
revisión. El upgrade es deliberadamente idempotente y no reinterpreta importes
legacy: crea únicamente los companions de semántica e integridad que falten.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260824_0041"
down_revision = "20260812_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "billing_charge_breakdowns" not in tables:
        op.create_table(
            "billing_charge_breakdowns",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("billing_invoices.id"), nullable=False),
            sa.Column("charge_type", sa.String(40), nullable=False, server_default="Legacy"),
            sa.Column("amount_semantics", sa.String(40), nullable=False, server_default="legacy_unknown"),
            sa.Column("net_amount", sa.Float(), nullable=True),
            sa.Column("tax_rate_snapshot", sa.Float(), nullable=True),
            sa.Column("tax_amount", sa.Float(), nullable=True),
            sa.Column("total_amount", sa.Float(), nullable=True),
            sa.Column("source_reference", sa.String(120), nullable=False, server_default=""),
            sa.Column("classification_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("invoice_id", name="uq_billing_charge_breakdown_invoice"),
        )
        op.create_index("ix_billing_charge_breakdowns_invoice_id", "billing_charge_breakdowns", ["invoice_id"])
        op.create_index("ix_billing_charge_breakdowns_amount_semantics", "billing_charge_breakdowns", ["amount_semantics"])

    tables = set(inspect(bind).get_table_names())
    if "contract_signature_snapshots" not in tables:
        op.create_table(
            "contract_signature_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("service_contracts.id"), nullable=False),
            sa.Column("signature_version", sa.String(20), nullable=False, server_default="1.1"),
            sa.Column("canonical_payload", sa.Text(), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("contract_id", name="uq_contract_signature_snapshot_contract"),
        )
        op.create_index("ix_contract_signature_snapshots_contract_id", "contract_signature_snapshots", ["contract_id"])
        op.create_index("ix_contract_signature_snapshots_payload_hash", "contract_signature_snapshots", ["payload_hash"])


def downgrade() -> None:
    # No eliminamos automáticamente evidencia contractual ni clasificación de cobro.
    # La precisión monetaria se migrará de forma deliberada en V2.60.7.
    return
