from __future__ import annotations

from sqlalchemy import DateTime, Float, String, Text, select
from sqlalchemy.orm import mapped_column

from ..base import Base
from .commercial import BillingInvoice, ServiceContract


# V2.60.6 extends the existing authorities instead of creating one-to-one tables.
# Nullable columns are deliberate: historical rows remain unknown until there is
# evidence to classify them. No legacy amount or signature is reinterpreted.
BillingInvoice.charge_type = mapped_column(String(40), nullable=True)
BillingInvoice.amount_semantics = mapped_column(String(40), nullable=True)
BillingInvoice.net_amount = mapped_column(Float, nullable=True)
BillingInvoice.tax_rate_snapshot = mapped_column(Float, nullable=True)
BillingInvoice.tax_amount = mapped_column(Float, nullable=True)
BillingInvoice.total_amount = mapped_column(Float, nullable=True)
BillingInvoice.source_reference = mapped_column(String(120), nullable=True)
BillingInvoice.classification_note = mapped_column(Text, nullable=True)
BillingInvoice.semantics_created_at = mapped_column(DateTime, nullable=True)

ServiceContract.signature_version = mapped_column(String(20), nullable=True)
ServiceContract.signature_payload = mapped_column(Text, nullable=True)
ServiceContract.signature_snapshot_created_at = mapped_column(DateTime, nullable=True)


# Read-only compatibility projections preserve the semantic language used by
# Revenue Operations tests and query code without adding physical ORM tables.
_billing_projection = (
    select(
        BillingInvoice.id.label("invoice_id"),
        BillingInvoice.charge_type,
        BillingInvoice.amount_semantics,
        BillingInvoice.net_amount,
        BillingInvoice.tax_rate_snapshot,
        BillingInvoice.tax_amount,
        BillingInvoice.total_amount,
        BillingInvoice.source_reference,
        BillingInvoice.classification_note,
        BillingInvoice.semantics_created_at.label("created_at"),
    )
    .where(BillingInvoice.amount_semantics.is_not(None))
    .subquery("billing_charge_breakdown_projection")
)


class BillingChargeBreakdown(Base):
    """Read-only semantic projection over ``billing_invoices``.

    The write authority is ``BillingInvoice`` itself. Rows without
    ``amount_semantics`` are intentionally absent and therefore remain legacy
    unknown rather than being auto-classified.
    """

    __table__ = _billing_projection
    __mapper_args__ = {"primary_key": [_billing_projection.c.invoice_id]}


_contract_signature_projection = (
    select(
        ServiceContract.id.label("contract_id"),
        ServiceContract.signature_version,
        ServiceContract.signature_payload.label("canonical_payload"),
        ServiceContract.signature_hash.label("payload_hash"),
        ServiceContract.signature_snapshot_created_at.label("created_at"),
    )
    .where(ServiceContract.signature_version.is_not(None))
    .subquery("contract_signature_snapshot_projection")
)


class ContractSignatureSnapshot(Base):
    """Read-only canonical-signature projection over ``service_contracts``."""

    __table__ = _contract_signature_projection
    __mapper_args__ = {"primary_key": [_contract_signature_projection.c.contract_id]}
