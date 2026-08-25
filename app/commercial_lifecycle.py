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


def _allowed_targets(matrix: dict[str, frozenset[str]], current: str, label: str) -> frozenset[str]:
    allowed = matrix.get(current)
    if allowed is None:
        raise LifecycleTransitionError(
            f"El estado actual de {label} ({current or 'vacío'}) no pertenece al ciclo de vida autoritativo; "
            "no se reescribe automáticamente."
        )
    return allowed


def _validate_transition(
    matrix: dict[str, frozenset[str]],
    current: str,
    target: str,
    label: str,
) -> None:
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
        raise LifecycleTransitionError(
            f"La propuesta está en estado {status or 'desconocido'} y ya no admite {action}."
        )


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


def validate_contract_transition(contract: Any, target: str, *, allow_renewal: bool = False) -> None:
    current = getattr(contract, "status", "")
    if target == current:
        return
    _validate_transition(CONTRACT_TRANSITIONS, current, target, "contrato")
    if target == "Renovado" and not allow_renewal:
        raise LifecycleTransitionError(
            "El estado Renovado solo puede generarse al crear una renovación contractual vinculada."
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


def validate_order_transition(order: Any, target: str) -> None:
    _validate_transition(ORDER_TRANSITIONS, getattr(order, "status", ""), target, "orden de servicio")
    if target == "Aceptada" and not getattr(order, "delivered_at", None):
        raise LifecycleTransitionError("Una orden no puede quedar Aceptada sin evidencia previa de entrega.")


def validate_invoice_transition(invoice: Any, target: str) -> None:
    current = getattr(invoice, "status", "")
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


def validate_document_transition(document: Any, target: str) -> None:
    _validate_transition(DOCUMENT_TRANSITIONS, getattr(document, "status", ""), target, "documento de cobro")
    if target == "Emitido externamente":
        provider = (getattr(document, "provider", "") or "").strip()
        external_number = (getattr(document, "external_number", "") or "").strip()
        if not provider or provider == "Sin integración":
            raise LifecycleTransitionError("La emisión externa requiere identificar el proveedor autorizado.")
        if not external_number or not getattr(document, "issued_at", None):
            raise LifecycleTransitionError(
                "La emisión externa requiere número externo y fecha de emisión persistidos."
            )


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


def _reject_rewrite_of_established(state: Any, field_names: Iterable[str], label: str) -> None:
    for field_name in field_names:
        history = state.attrs[field_name].history
        if not history.has_changes() or not history.deleted:
            continue
        previous = history.deleted[0]
        if previous not in (None, ""):
            raise LifecycleTransitionError(
                f"La evidencia establecida de {label} ({field_name}) no puede sobrescribirse."
            )


def _renewal_child_exists(session: Session, contract: Any) -> bool:
    contract_id = getattr(contract, "id", None)
    if contract_id is None:
        return False
    from .db.models import ServiceContract

    for candidate in session.new:
        if isinstance(candidate, ServiceContract) and getattr(candidate, "parent_contract_id", None) == contract_id:
            return True
    return False


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
            _reject_rewrite_of_established(
                state,
                ("accepted_by", "accepted_email", "accepted_ip", "accepted_at", "acceptance_hash"),
                "aceptación de propuesta",
            )
            if state.attrs.status.history.has_changes():
                validate_proposal_transition(_history_previous(state, "status"), obj.status)

        elif isinstance(obj, PaymentTransaction):
            _reject_rewrite_of_established(state, ("paid_at",), "pago")
            if state.attrs.status.history.has_changes():
                validate_payment_transition(_history_previous(state, "status"), obj.status)

        elif isinstance(obj, ServiceContract):
            _reject_rewrite_of_established(
                state,
                (
                    "signed_by", "signed_email", "signed_at", "signature_hash", "signature_version",
                    "signature_payload", "signature_snapshot_created_at",
                ),
                "firma contractual",
            )
            if state.attrs.status.history.has_changes():
                validate_contract_transition(
                    obj,
                    obj.status,
                    allow_renewal=(obj.status == "Renovado" and _renewal_child_exists(session, obj)),
                )

        elif isinstance(obj, ServiceOrder):
            _reject_rewrite_of_established(state, ("delivered_at", "accepted_at"), "entrega de orden")
            if state.attrs.status.history.has_changes():
                previous = _history_previous(state, "status")
                # validate against the previous persisted state while retaining
                # evidence written in the same transaction.
                current_status = obj.status
                obj.status = previous
                try:
                    validate_order_transition(obj, current_status)
                finally:
                    obj.status = current_status

        elif isinstance(obj, BillingInvoice):
            _reject_rewrite_of_established(state, ("paid_at",), "pago de cobro")
            if state.attrs.status.history.has_changes():
                previous = _history_previous(state, "status")
                current_status = obj.status
                obj.status = previous
                try:
                    validate_invoice_transition(obj, current_status)
                finally:
                    obj.status = current_status

        elif isinstance(obj, BillingDocumentRecord):
            _reject_rewrite_of_established(
                state,
                ("provider", "external_number", "issued_at", "cufe", "document_url"),
                "emisión externa",
            )
            if state.attrs.status.history.has_changes():
                previous = _history_previous(state, "status")
                current_status = obj.status
                obj.status = previous
                try:
                    validate_document_transition(obj, current_status)
                finally:
                    obj.status = current_status

        elif isinstance(obj, CollectionAction):
            if _history_previous(state, "status") == "Completada":
                if any(state.attrs[name].history.has_changes() for name in ("status", "result", "completed_at")):
                    raise LifecycleTransitionError(
                        "La gestión de cartera completada es evidencia histórica y no puede sobrescribirse."
                    )
            if state.attrs.status.history.has_changes() and obj.status == "Completada":
                ensure_collection_can_complete(obj, obj.result)
    except LifecycleTransitionError as exc:
        raise LifecyclePersistenceConflict(str(exc)) from exc


@event.listens_for(Session, "before_flush")
def _enforce_commercial_lifecycle_before_flush(session: Session, flush_context, instances) -> None:
    """Fail closed on contradictory lifecycle writes before any SQL is emitted.

    Existing rows are never normalized or rewritten. Only dirty persisted rows
    are inspected, making this a forward-write contract compatible with legacy
    records while protecting newly established commercial evidence.
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
