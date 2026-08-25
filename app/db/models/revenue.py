from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event, inspect as sa_inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from ..base import Base
from ..monetary_types import ExactDecimal, ExactNumeric
from .commercial import (
    BillingInvoice,
    CommercialProposal,
    OrganizationSubscription,
    PaymentTransaction,
    RenewalOpportunity,
    ServiceContract,
    ServicePlan,
)

# Importing the canonical model facade must also register the commercial
# lifecycle Session guard. The lifecycle module has no eager dependency on the
# model facade, so this side-effect import is cycle-safe and covers web, scripts,
# jobs and tests that create Session objects without importing a route module.
from ... import commercial_lifecycle as _commercial_lifecycle  # noqa: E402,F401


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


def _restore_exact_runtime_values(target: object, field_names: tuple[str, ...]) -> None:
    """Restore ExactDecimal semantics without making a clean ORM row dirty.

    Some SQLAlchemy dialects adapt ``Numeric`` and can therefore return a base
    ``Decimal`` even though the canonical type has a result processor. The
    economic value and scale are already correct at that point; this hook only
    restores the compatibility subtype used by historical arithmetic and
    presentation. ``set_committed_value`` deliberately avoids UPDATE churn.
    """

    for field_name in field_names:
        value = getattr(target, field_name, None)
        if value is None or isinstance(value, ExactDecimal):
            continue
        if isinstance(value, Decimal):
            set_committed_value(target, field_name, ExactDecimal(value))


def _restore_loaded_exact_runtime_values(target: object, context) -> None:
    _restore_exact_runtime_values(target, _EXACT_NUMERIC_FIELDS.get(type(target), ()))


def _restore_refreshed_exact_runtime_values(target: object, context, attrs) -> None:
    field_names = _EXACT_NUMERIC_FIELDS.get(type(target), ())
    if attrs:
        refreshed = set(attrs)
        field_names = tuple(name for name in field_names if name in refreshed)
    _restore_exact_runtime_values(target, field_names)


for _model in _EXACT_NUMERIC_FIELDS:
    event.listen(_model, "load", _restore_loaded_exact_runtime_values)
    event.listen(_model, "refresh", _restore_refreshed_exact_runtime_values)


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
            if normalized != value or not isinstance(value, ExactDecimal):
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


__all__ = [
    "BillingChargeBreakdown",
    "ContractSignatureSnapshot",
    "ExactDecimal",
    "ExactNumeric",
]