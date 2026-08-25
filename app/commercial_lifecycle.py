from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException
from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.orm import Session

from .revenue_operations import INVOICE_TOTAL_WITH_TAX


class LifecycleTransitionError(ValueError):
    """Raised when a requested lifecycle transition contradicts established facts."""


class LifecyclePersistenceConflict(HTTPException):
    """HTTP-safe persistence boundary for lifecycle violations discovered at flush."""

    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)


PROPOSAL_OPEN_STATES = frozenset({"Borrador", "Enviada", "Vista"})
PROPOSAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "Borrador": frozenset({"Borrador", "Enviada", "Aceptada", "Rechazada", "Vencida"}),
    "Enviada": frozenset({"Enviada", "Vista", "Aceptada", "Rechazada", "Vencida"}),
    "Vista": frozenset({"Vista", "Aceptada", "Rechazada", "Vencida"}),
    "Aceptada": frozenset({"Aceptada"}),
    "Rechazada": frozenset({"Rechazada"}),
    "Vencida": frozenset({"Vencida"}),
}

PAYMENT_PROVIDER_STATUS = {
    "paid": "Pagada",
    "approved": "Pagada",
    "pending": "Pendiente",
    "failed": "Fallida",
    "declined": "Fallida",
    "refunded": "Reembolsada",
}
PAYMENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "Pendiente": frozenset({"Pendiente", "Pagada", "Fallida"}),
    "Fallida": frozenset({"Fallida", "Pendiente", "Pagada"}),
    "Pagada": frozenset({"Pagada", "Reembolsada"}),
    "Reembolsada": frozenset({"Reembolsada"}),
}

CONTRACT_TRANSITIONS: dict[str, frozenset[str]] = {
    "Borrador": frozenset({"Borrador", "Vigente", "Terminado"}),
    "Vigente": frozenset({"Vigente", "Suspendido", "Terminado", "Renovado"}),
    "Suspendido": frozenset({"Suspendido", "Vigente", "Terminado"}),
    "Terminado": frozenset({"Terminado", "Renovado"}),
    "Renovado": frozenset({"Renovado"}),
}

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "Planeada": frozenset({"Planeada", "En ejecución", "Bloqueada", "Cancelada"}),
    "En ejecución": frozenset({"En ejecución", "Bloqueada", "Entregada", "Cancelada"}),
    "Bloqueada": frozenset({"Bloqueada", "En ejecución", "Cancelada"}),
    "Entregada": frozenset({"Entregada", "En ejecución", "Aceptada"}),
    "Aceptada": frozenset({"Aceptada"}),
    "Cancelada": frozenset({"Cancelada"}),
}

INVOICE_TRANSITIONS: dict[str, frozenset[str]] = {
    "Pendiente": frozenset({"Pendiente", "Vencida", "Pagada", "Anulada"}),
    "Vencida": frozenset({"Vencida", "Pendiente", "Pagada", "Anulada"}),
    "Pagada": frozenset({"Pagada"}),
    "Anulada": frozenset({"Anulada"}),
}

DOCUMENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "Borrador": frozenset({"Borrador", "Pendiente de integración", "Emitido externamente", "Anulado"}),
    "Pendiente de integración": frozenset({"Pendiente de integración", "Emitido externamente", "Rechazado", "Anulado"}),
    "Rechazado": frozenset({"Rechazado", "Pendiente de integración", "Emitido externamente", "Anulado"}),
    "Emitido externamente": frozenset({"Emitido externamente", "Anulado"}),
    "Anulado": frozenset({"Anulado"}),
}

# These fields are the evidence envelope behind the canonical hashes. Once the
# corresponding milestone existed before the current flush, changing any bound
# field would make the persisted hash describe a different business fact.
PROPOSAL_ACCEPTANCE_BOUND_FIELDS = (
    "reference",
    "contract_version",
    "billing_cycle",
    "implementation_fee",
    "recurring_fee",
    "discount_amount",
    "tax_rate",
    "first_year_total",
    "scope_json",
    "deliverables_json",
    "terms",
    "accepted_by",
    "accepted_email",
    "accepted_at",
    "accepted_ip",
    "acceptance_hash",
)
CONTRACT_SIGNATURE_BOUND_FIELDS = (
    "reference",
    "organization_id",
    "proposal_id",
    "parent_contract_id",
    "title",
    "version",
    "start_date",
    "end_date",
    "renewal_type",
    "auto_renew",
    "notice_days",
    "contract_value",
    "billing_cycle",
    "owner",
    "terms_snapshot",
    "signed_by",
    "signed_email",
    "signed_at",
    "signature_hash",
    "signature_version",
    "signature_payload",
    "signature_snapshot_created_at",
)
PAYMENT_SETTLEMENT_BOUND_FIELDS = (
    "amount",
    "currency",
    "external_reference",
    "paid_at",
)


def _allowed_targets(matrix: dict[str, frozenset[str]], current: str, label: str) -> frozenset[str]:
    allowed = matrix.get(current)
    if allowed is None:
        raise LifecycleTransitionError(
            f"El estado actual de {label} ({current or 'vacío'}) no pertenece al ciclo de vida autoritativo; "
            "no se reescribe automáticamente."
        )
    return allowed


def _validate_transition(matrix: dict[str, frozenset[str]], current: str, target: str, label: str) -> None:
    allowed = _allowed_targets(matrix, current, label)
    if target not in allowed:
        raise LifecycleTransitionError(f"Transición de {label} no permitida: {current} → {target}.")


def ensure_proposal_can_send(proposal: Any) -> None:
    if getattr(proposal, "status", "") != "Borrador":
        raise LifecycleTransitionError(
            "Solo una propuesta en Borrador puede marcarse como enviada; los hitos posteriores no se retroceden."
        )
    if getattr(proposal, "acceptance_hash", "") or getattr(proposal, "accepted_at", None):
        raise LifecycleTransitionError(
            "La propuesta ya conserva evidencia de aceptación y no puede volver al flujo de envío."
        )


def ensure_proposal_can_decide(proposal: Any, *, action: str) -> None:
    status = getattr(proposal, "status", "")
    if getattr(proposal, "acceptance_hash", "") or getattr(proposal, "accepted_at", None):
        raise LifecycleTransitionError(
            "La aceptación de esta propuesta ya quedó registrada y su evidencia no puede sobrescribirse."
        )
    if status not in PROPOSAL_OPEN_STATES:
        raise LifecycleTransitionError(f"La propuesta está en estado {status or 'desconocido'} y ya no admite {action}.")


def validate_proposal_transition(current: str, target: str) -> None:
    _validate_transition(PROPOSAL_TRANSITIONS, current, target, "propuesta")


def normalize_payment_provider_status(raw_status: str) -> str:
    normalized = (raw_status or "").strip().lower()
    try:
        return PAYMENT_PROVIDER_STATUS[normalized]
    except KeyError as exc:
        raise LifecycleTransitionError(
            f"Estado de pago del proveedor no soportado: {raw_status or 'vacío'}."
        ) from exc


def validate_payment_transition(current: str, target: str) -> None:
    _validate_transition(PAYMENT_TRANSITIONS, current, target, "pago")


def payment_is_terminal(status: str) -> bool:
    return status in {"Pagada", "Reembolsada"}


def contract_allowed_targets(contract: Any) -> tuple[str, ...]:
    current = getattr(contract, "status", "")
    allowed = set(_allowed_targets(CONTRACT_TRANSITIONS, current, "contrato"))
    allowed.discard("Renovado")
    if "Vigente" in allowed and not contract_has_signature_evidence(contract):
        allowed.discard("Vigente")
    order = ("Borrador", "Vigente", "Suspendido", "Terminado", "Renovado")
    return tuple(item for item in order if item in allowed)


def contract_has_signature_evidence(contract: Any) -> bool:
    return bool(
        getattr(contract, "signature_hash", "")
        and getattr(contract, "signed_at", None)
        and getattr(contract, "signed_by", "")
        and getattr(contract, "signed_email", "")
    )


def ensure_contract_can_sign(contract: Any, *, has_snapshot: bool = False) -> None:
    if getattr(contract, "status", "") != "Borrador":
        raise LifecycleTransitionError("Solo un contrato en Borrador puede registrar una nueva firma.")
    if contract_has_signature_evidence(contract) or getattr(contract, "signature_hash", "") or has_snapshot:
        raise LifecycleTransitionError("El contrato ya conserva evidencia de firma y no puede volver a firmarse.")


def validate_contract_transition(
    contract: Any,
    target: str,
    *,
    current_status: str | None = None,
    allow_renewal: bool = False,
) -> None:
    current = current_status if current_status is not None else getattr(contract, "status", "")
    if target == current:
        return
    _validate_transition(CONTRACT_TRANSITIONS, current, target, "contrato")
    if target == "Renovado":
        if not allow_renewal:
            raise LifecycleTransitionError(
                "El estado Renovado solo puede generarse al crear una renovación contractual vinculada."
            )
        if not contract_has_signature_evidence(contract):
            raise LifecycleTransitionError(
                "No se puede consolidar una renovación desde un contrato sin evidencia de firma persistida."
            )
    if target == "Vigente" and not contract_has_signature_evidence(contract):
        raise LifecycleTransitionError(
            "Un contrato no puede quedar Vigente sin identidad, fecha y hash de firma persistidos."
        )
    if target == "Borrador" and contract_has_signature_evidence(contract):
        raise LifecycleTransitionError("Un contrato firmado no puede regresar a Borrador.")


def ensure_contract_can_renew(contract: Any) -> None:
    if getattr(contract, "status", "") not in {"Vigente", "Terminado"}:
        raise LifecycleTransitionError("Solo pueden renovarse contratos vigentes o terminados.")
    if not contract_has_signature_evidence(contract):
        raise LifecycleTransitionError(
            "No se puede crear una renovación desde un contrato sin evidencia de firma persistida."
        )


def order_allowed_targets(order: Any) -> tuple[str, ...]:
    current = getattr(order, "status", "")
    allowed = _allowed_targets(ORDER_TRANSITIONS, current, "orden de servicio")
    sequence = ("Planeada", "En ejecución", "Bloqueada", "Entregada", "Aceptada", "Cancelada")
    return tuple(item for item in sequence if item in allowed)


def validate_order_transition(order: Any, target: str, *, current_status: str | None = None) -> None:
    current = current_status if current_status is not None else getattr(order, "status", "")
    _validate_transition(ORDER_TRANSITIONS, current, target, "orden de servicio")
    if target == "Aceptada" and not getattr(order, "delivered_at", None):
        raise LifecycleTransitionError("Una orden no puede quedar Aceptada sin evidencia previa de entrega.")


def validate_invoice_transition(invoice: Any, target: str, *, current_status: str | None = None) -> None:
    current = current_status if current_status is not None else getattr(invoice, "status", "")
    _validate_transition(INVOICE_TRANSITIONS, current, target, "cobro")
    if target == "Pagada" and current != "Pagada":
        if getattr(invoice, "amount_semantics", None) != INVOICE_TOTAL_WITH_TAX:
            raise LifecycleTransitionError(
                "Solo un cobro con total económico conocido puede marcarse como Pagada desde esta gestión."
            )
        if getattr(invoice, "total_amount", None) is None:
            raise LifecycleTransitionError(
                "El cobro declara total conocido pero no conserva un total_amount autoritativo."
            )


def document_allowed_targets(document: Any) -> tuple[str, ...]:
    current = getattr(document, "status", "")
    allowed = _allowed_targets(DOCUMENT_TRANSITIONS, current, "documento de cobro")
    sequence = ("Borrador", "Pendiente de integración", "Emitido externamente", "Rechazado", "Anulado")
    return tuple(item for item in sequence if item in allowed)


def validate_document_transition(document: Any, target: str, *, current_status: str | None = None) -> None:
    current = current_status if current_status is not None else getattr(document, "status", "")
    _validate_transition(DOCUMENT_TRANSITIONS, current, target, "documento de cobro")
    if target == "Emitido externamente":
        provider = (getattr(document, "provider", "") or "").strip()
        external_number = (getattr(document, "external_number", "") or "").strip()
        if not provider or provider == "Sin integración":
            raise LifecycleTransitionError("La emisión externa requiere identificar el proveedor autorizado.")
        if not external_number or not getattr(document, "issued_at", None):
            raise LifecycleTransitionError("La emisión externa requiere número externo y fecha de emisión persistidos.")


def ensure_collection_can_complete(action: Any, result: str) -> str:
    if getattr(action, "status", "") != "Pendiente":
        raise LifecycleTransitionError("La gestión de cartera ya fue completada y su resultado no puede sobrescribirse.")
    clean_result = (result or "").strip()
    if not clean_result:
        raise LifecycleTransitionError("Registra un resultado antes de completar la gestión de cartera.")
    return clean_result


def ordered_existing(values: Iterable[str], preferred_order: Iterable[str]) -> tuple[str, ...]:
    existing = set(values)
    return tuple(item for item in preferred_order if item in existing)


def _history_previous(state: Any, field_name: str) -> Any:
    history = state.attrs[field_name].history
    if history.deleted:
        return history.deleted[0]
    return getattr(state.object, field_name, None)


def _field_existed_before_flush(state: Any, field_name: str) -> bool:
    history = state.attrs[field_name].history
    if history.has_changes():
        previous = history.deleted[0] if history.deleted else None
        return previous not in (None, "")
    return getattr(state.object, field_name, None) not in (None, "")


def _field_becoming_established(state: Any, field_name: str) -> bool:
    history = state.attrs[field_name].history
    if not history.has_changes():
        return False
    previous = history.deleted[0] if history.deleted else None
    current = getattr(state.object, field_name, None)
    return previous in (None, "") and current not in (None, "")


def _milestone_existed_before_flush(state: Any, field_names: Iterable[str]) -> bool:
    return any(_field_existed_before_flush(state, field_name) for field_name in field_names)


def _reject_any_changes(state: Any, field_names: Iterable[str], label: str) -> None:
    for field_name in field_names:
        if state.attrs[field_name].history.has_changes():
            raise LifecycleTransitionError(
                f"La evidencia consolidada de {label} vincula {field_name}; ese campo no puede sobrescribirse."
            )


def _reject_rewrite_of_established(state: Any, field_names: Iterable[str], label: str) -> None:
    for field_name in field_names:
        history = state.attrs[field_name].history
        if not history.has_changes() or not history.deleted:
            continue
        previous = history.deleted[0]
        if previous not in (None, ""):
            raise LifecycleTransitionError(f"La evidencia establecida de {label} ({field_name}) no puede sobrescribirse.")


def _renewal_child_exists(session: Session, contract: Any) -> bool:
    contract_id = getattr(contract, "id", None)
    if contract_id is None:
        return False
    from .db.models import ServiceContract

    return any(
        isinstance(candidate, ServiceContract) and getattr(candidate, "parent_contract_id", None) == contract_id
        for candidate in session.new
    )


def _order_had_persisted_delivery(state: Any) -> bool:
    history = state.attrs.delivered_at.history
    if history.has_changes():
        previous = history.deleted[0] if history.deleted else None
        return previous not in (None, "")
    return getattr(state.object, "delivered_at", None) is not None


def _enforce_dirty_lifecycle(session: Session, obj: Any) -> None:
    from .db.models import (
        BillingDocumentRecord,
        BillingInvoice,
        CollectionAction,
        CommercialProposal,
        PaymentTransaction,
        ServiceContract,
        ServiceOrder,
    )

    state = sa_inspect(obj)
    try:
        if isinstance(obj, CommercialProposal):
            if _milestone_existed_before_flush(state, ("acceptance_hash", "accepted_at")):
                _reject_any_changes(state, PROPOSAL_ACCEPTANCE_BOUND_FIELDS, "aceptación de propuesta")
            else:
                _reject_rewrite_of_established(
                    state,
                    ("accepted_by", "accepted_email", "accepted_ip", "accepted_at", "acceptance_hash"),
                    "aceptación de propuesta",
                )
            if state.attrs.status.history.has_changes():
                validate_proposal_transition(_history_previous(state, "status"), obj.status)

        elif isinstance(obj, PaymentTransaction):
            if _field_existed_before_flush(state, "paid_at"):
                _reject_any_changes(state, PAYMENT_SETTLEMENT_BOUND_FIELDS, "liquidación de pago")
            else:
                _reject_rewrite_of_established(state, ("paid_at",), "pago")
            if state.attrs.status.history.has_changes():
                validate_payment_transition(_history_previous(state, "status"), obj.status)

        elif isinstance(obj, ServiceContract):
            signature_preexisted = _milestone_existed_before_flush(state, ("signature_hash", "signed_at"))
            signature_becoming_established = _field_becoming_established(state, "signature_hash")
            if signature_preexisted:
                _reject_any_changes(state, CONTRACT_SIGNATURE_BOUND_FIELDS, "firma contractual")
            else:
                _reject_rewrite_of_established(
                    state,
                    (
                        "signed_by", "signed_email", "signed_at", "signature_hash", "signature_version",
                        "signature_payload", "signature_snapshot_created_at",
                    ),
                    "firma contractual",
                )
            previous_status = (
                _history_previous(state, "status")
                if state.attrs.status.history.has_changes()
                else obj.status
            )
            if signature_becoming_established:
                if previous_status != "Borrador":
                    raise LifecycleTransitionError(
                        "Una nueva firma contractual solo puede originarse desde un contrato en Borrador."
                    )
                if obj.status != "Vigente":
                    raise LifecycleTransitionError(
                        "La firma contractual debe completar el handoff Borrador → Vigente en la misma transacción."
                    )
                if not contract_has_signature_evidence(obj):
                    raise LifecycleTransitionError(
                        "La nueva firma contractual requiere identidad, correo, fecha y hash completos."
                    )
            if state.attrs.status.history.has_changes():
                validate_contract_transition(
                    obj,
                    obj.status,
                    current_status=previous_status,
                    allow_renewal=(obj.status == "Renovado" and _renewal_child_exists(session, obj)),
                )

        elif isinstance(obj, ServiceOrder):
            _reject_rewrite_of_established(state, ("delivered_at", "accepted_at"), "entrega de orden")
            if state.attrs.status.history.has_changes():
                previous_status = _history_previous(state, "status")
                if obj.status == "Aceptada" and not _order_had_persisted_delivery(state):
                    raise LifecycleTransitionError(
                        "Una orden solo puede aceptarse cuando la evidencia de entrega ya fue persistida previamente."
                    )
                validate_order_transition(obj, obj.status, current_status=previous_status)

        elif isinstance(obj, BillingInvoice):
            _reject_rewrite_of_established(state, ("paid_at",), "pago de cobro")
            if state.attrs.status.history.has_changes():
                validate_invoice_transition(obj, obj.status, current_status=_history_previous(state, "status"))

        elif isinstance(obj, BillingDocumentRecord):
            previous_status = _history_previous(state, "status") if state.attrs.status.history.has_changes() else obj.status
            if previous_status in {"Emitido externamente", "Anulado"}:
                _reject_rewrite_of_established(
                    state,
                    ("provider", "external_number", "issued_at", "cufe", "document_url"),
                    "emisión externa",
                )
            if state.attrs.status.history.has_changes():
                validate_document_transition(obj, obj.status, current_status=previous_status)

        elif isinstance(obj, CollectionAction):
            previous_status = _history_previous(state, "status") if state.attrs.status.history.has_changes() else obj.status
            if previous_status == "Completada":
                if any(state.attrs[name].history.has_changes() for name in ("status", "result", "completed_at")):
                    raise LifecycleTransitionError(
                        "La gestión de cartera completada es evidencia histórica y no puede sobrescribirse."
                    )
            elif state.attrs.status.history.has_changes():
                if previous_status != "Pendiente" or obj.status != "Completada":
                    raise LifecycleTransitionError(
                        f"Transición de gestión de cartera no permitida: {previous_status} → {obj.status}."
                    )
                if not (obj.result or "").strip():
                    raise LifecycleTransitionError("Registra un resultado antes de completar la gestión de cartera.")
    except LifecycleTransitionError as exc:
        raise LifecyclePersistenceConflict(str(exc)) from exc


@event.listens_for(Session, "before_flush")
def _enforce_commercial_lifecycle_before_flush(session: Session, flush_context, instances) -> None:
    """Fail closed on contradictory lifecycle writes before any SQL is emitted.

    Existing rows are never normalized or rewritten. Only dirty persisted rows
    are inspected, making this a forward-transition contract compatible with
    legacy records while protecting newly established commercial evidence.
    """

    for obj in tuple(session.dirty):
        _enforce_dirty_lifecycle(session, obj)


__all__ = [
    "LifecycleTransitionError",
    "LifecyclePersistenceConflict",
    "PROPOSAL_OPEN_STATES",
    "PROPOSAL_TRANSITIONS",
    "PAYMENT_PROVIDER_STATUS",
    "PAYMENT_TRANSITIONS",
    "CONTRACT_TRANSITIONS",
    "ORDER_TRANSITIONS",
    "INVOICE_TRANSITIONS",
    "DOCUMENT_TRANSITIONS",
    "PROPOSAL_ACCEPTANCE_BOUND_FIELDS",
    "CONTRACT_SIGNATURE_BOUND_FIELDS",
    "PAYMENT_SETTLEMENT_BOUND_FIELDS",
    "ensure_proposal_can_send",
    "ensure_proposal_can_decide",
    "validate_proposal_transition",
    "normalize_payment_provider_status",
    "validate_payment_transition",
    "payment_is_terminal",
    "contract_has_signature_evidence",
    "contract_allowed_targets",
    "ensure_contract_can_sign",
    "validate_contract_transition",
    "ensure_contract_can_renew",
    "order_allowed_targets",
    "validate_order_transition",
    "validate_invoice_transition",
    "document_allowed_targets",
    "validate_document_transition",
    "ensure_collection_can_complete",
    "ordered_existing",
]