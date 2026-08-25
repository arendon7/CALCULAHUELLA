from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .revenue_operations import INVOICE_TOTAL_WITH_TAX


class LifecycleTransitionError(ValueError):
    """Raised when a new write would contradict an already-established lifecycle fact."""


PROPOSAL_OPEN_STATES = frozenset({"Borrador", "Enviada", "Vista"})

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
    # Vigente from Borrador is only possible for an already-signed legacy row;
    # canonical signing uses the dedicated signature route.
    "Borrador": frozenset({"Borrador", "Vigente", "Terminado"}),
    "Vigente": frozenset({"Vigente", "Suspendido", "Terminado"}),
    "Suspendido": frozenset({"Suspendido", "Vigente", "Terminado"}),
    "Terminado": frozenset({"Terminado"}),
    # The only canonical way to create Renovado is the renewal route, which
    # simultaneously creates the child contract. Generic status writes cannot
    # manufacture that evidence.
    "Renovado": frozenset({"Renovado"}),
}

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "Planeada": frozenset({"Planeada", "En ejecución", "Bloqueada", "Cancelada"}),
    "En ejecución": frozenset({"En ejecución", "Bloqueada", "Entregada", "Cancelada"}),
    "Bloqueada": frozenset({"Bloqueada", "En ejecución", "Cancelada"}),
    # Re-open for rework is explicit; acceptance itself is terminal.
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
        raise LifecycleTransitionError(
            f"Transición de {label} no permitida: {current} → {target}."
        )


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
    if current != "Renovado":
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


def validate_contract_transition(contract: Any, target: str) -> None:
    current = getattr(contract, "status", "")
    if target == current:
        return
    _validate_transition(CONTRACT_TRANSITIONS, current, target, "contrato")
    if target == "Renovado":
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


def ensure_collection_can_complete(action: Any, result: str) -> str:
    if getattr(action, "status", "") != "Pendiente":
        raise LifecycleTransitionError("La gestión de cartera ya fue completada y su resultado no puede sobrescribirse.")
    clean_result = (result or "").strip()
    if not clean_result:
        raise LifecycleTransitionError("Registra un resultado antes de completar la gestión de cartera.")
    return clean_result


def ordered_existing(values: Iterable[str], preferred_order: Iterable[str]) -> tuple[str, ...]:
    """Small helper kept public for UI projections without inventing states."""
    existing = set(values)
    return tuple(item for item in preferred_order if item in existing)


__all__ = [
    "LifecycleTransitionError",
    "PROPOSAL_OPEN_STATES",
    "PAYMENT_PROVIDER_STATUS",
    "PAYMENT_TRANSITIONS",
    "CONTRACT_TRANSITIONS",
    "ORDER_TRANSITIONS",
    "INVOICE_TRANSITIONS",
    "DOCUMENT_TRANSITIONS",
    "ensure_proposal_can_send",
    "ensure_proposal_can_decide",
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
