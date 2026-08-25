from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event, inspect as sa_inspect, select
from sqlalchemy.orm import Session

from ..base import Base
from ..monetary_types import ExactNumeric
from .commercial import (
    BillingInvoice,
    CommercialProposal,
    OrganizationSubscription,
    PaymentTransaction,
    RenewalOpportunity,
    ServiceContract,
    ServicePlan,
)


# V2.60.9 authoritative ORM write surface. V2.60.10 keeps enforcement here but
# the physical/ORM column authority now lives declaratively in commercial.py.
# Only new objects and monetary attributes that actually changed are normalized;
# unrelated updates therefore do not rewrite historical economic records.
_EXACT_NUMERIC_FIELDS: dict[type, tuple[str, ...]] = {
    ServicePlan: ("monthly_fee", "annual_fee"),
    OrganizationSubscription: ("custom_monthly_fee",),
    BillingInvoice: (
        "amount",
        "net_amount",
        "tax_rate_snapshot",
        "tax_amount",
        "total_amount",
    ),
    CommercialProposal: (
        "implementation_fee",
        "recurring_fee",
        "discount_amount",
        "tax_rate",
        "first_year_total",
    ),
    PaymentTransaction: ("amount",),
    ServiceContract: ("contract_value",),
    RenewalOpportunity: ("forecast_amount",),
}


@event.listens_for(Session, "before_flush")
def _enforce_exact_numeric_before_flush(session: Session, flush_context, instances) -> None:
    """Enforce economic invariants before dialect adaptation or SQL emission."""

    new_objects = set(session.new)
    candidates = new_objects | set(session.dirty)
    for obj in candidates:
        field_names = _EXACT_NUMERIC_FIELDS.get(type(obj))
        if not field_names:
            continue
        state = sa_inspect(obj)
        is_new = obj in new_objects
        for field_name in field_names:
            if not is_new and not state.attrs[field_name].history.has_changes():
                continue
            value = getattr(obj, field_name, None)
            if value is None:
                continue
            column_type = obj.__table__.c[field_name].type
            if not isinstance(column_type, ExactNumeric):
                raise RuntimeError(f"{type(obj).__name__}.{field_name} perdió su autoridad ExactNumeric")
            normalized = column_type.normalize_value(value)
            if normalized != value or not isinstance(value, Decimal):
                setattr(obj, field_name, normalized)


# Read-only compatibility projections preserve the semantic language used by
# Revenue Operations without adding one-to-one physical tables. The write
# authority remains the declaratively mapped commercial model itself.
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
    """Read-only semantic projection over ``billing_invoices``."""

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
