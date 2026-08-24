from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class BillingChargeBreakdown(Base):
    """Semantic companion for billing records without reinterpreting legacy amounts.

    Existing ``BillingInvoice.amount`` values predate an explicit net/tax/total
    contract. This table classifies only records for which the application has
    evidence of the amount semantics. Legacy rows can intentionally remain
    without a companion row.
    """

    __tablename__ = "billing_charge_breakdowns"
    __table_args__ = (UniqueConstraint("invoice_id", name="uq_billing_charge_breakdown_invoice"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("billing_invoices.id"), nullable=False, index=True)
    charge_type: Mapped[str] = mapped_column(String(40), default="Legacy")
    amount_semantics: Mapped[str] = mapped_column(String(40), default="legacy_unknown", index=True)
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_rate_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_reference: Mapped[str] = mapped_column(String(120), default="")
    classification_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    invoice = relationship("BillingInvoice")


class ContractSignatureSnapshot(Base):
    """Immutable canonical payload used for new service-contract signatures."""

    __tablename__ = "contract_signature_snapshots"
    __table_args__ = (UniqueConstraint("contract_id", name="uq_contract_signature_snapshot_contract"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("service_contracts.id"), nullable=False, index=True)
    signature_version: Mapped[str] = mapped_column(String(20), default="1.1")
    canonical_payload: Mapped[str] = mapped_column(Text)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    contract = relationship("ServiceContract")
