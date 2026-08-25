from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app.commercial_lifecycle import (
    LifecycleTransitionError,
    contract_allowed_targets,
    document_allowed_targets,
    ensure_collection_can_complete,
    ensure_contract_can_renew,
    ensure_contract_can_sign,
    ensure_proposal_can_decide,
    ensure_proposal_can_send,
    normalize_payment_provider_status,
    order_allowed_targets,
    payment_is_terminal,
    validate_contract_transition,
    validate_document_transition,
    validate_invoice_transition,
    validate_order_transition,
    validate_payment_transition,
)
from app.revenue_operations import INVOICE_BASE_BEFORE_TAX, INVOICE_TOTAL_WITH_TAX


def _signed_contract(status: str = "Vigente") -> NS:
    return NS(
        status=status,
        signature_hash="a" * 64,
        signed_at=datetime(2026, 8, 25, 15, 0, tzinfo=UTC),
        signed_by="Laura Firma",
        signed_email="laura@example.com",
    )


def _unsigned_contract(status: str = "Borrador") -> NS:
    return NS(
        status=status,
        signature_hash="",
        signed_at=None,
        signed_by="",
        signed_email="",
    )


def test_v26012_proposal_decision_preserves_existing_acceptance_evidence() -> None:
    accepted = NS(status="Aceptada", acceptance_hash="b" * 64, accepted_at=datetime.now(UTC))
    with pytest.raises(LifecycleTransitionError, match="evidencia no puede sobrescribirse"):
        ensure_proposal_can_decide(accepted, action="una nueva aceptación")
    with pytest.raises(LifecycleTransitionError):
        ensure_proposal_can_send(accepted)


def test_v26012_proposal_keeps_existing_borrador_direct_decision_contract() -> None:
    draft = NS(status="Borrador", acceptance_hash="", accepted_at=None)
    ensure_proposal_can_decide(draft, action="aceptación")
    ensure_proposal_can_send(draft)


def test_v26012_rejected_and_expired_proposals_are_terminal_for_new_decisions() -> None:
    for status in ("Rechazada", "Vencida"):
        proposal = NS(status=status, acceptance_hash="", accepted_at=None)
        with pytest.raises(LifecycleTransitionError, match="ya no admite"):
            ensure_proposal_can_decide(proposal, action="aceptación")


def test_v26012_payment_provider_status_is_closed_and_known() -> None:
    assert normalize_payment_provider_status(" approved ") == "Pagada"
    assert normalize_payment_provider_status("declined") == "Fallida"
    assert normalize_payment_provider_status("refunded") == "Reembolsada"
    with pytest.raises(LifecycleTransitionError, match="no soportado"):
        normalize_payment_provider_status("chargeback-ish")


def test_v26012_payment_transitions_preserve_terminal_evidence() -> None:
    validate_payment_transition("Pendiente", "Pagada")
    validate_payment_transition("Fallida", "Pagada")
    validate_payment_transition("Pagada", "Pagada")
    validate_payment_transition("Pagada", "Reembolsada")
    assert payment_is_terminal("Pagada")
    assert payment_is_terminal("Reembolsada")
    with pytest.raises(LifecycleTransitionError):
        validate_payment_transition("Pagada", "Pendiente")
    with pytest.raises(LifecycleTransitionError):
        validate_payment_transition("Reembolsada", "Pagada")
    with pytest.raises(LifecycleTransitionError, match="no pertenece"):
        validate_payment_transition("Estado legacy", "Pagada")


def test_v26012_unsigned_contract_cannot_claim_active_or_renewed_state() -> None:
    contract = _unsigned_contract()
    assert contract_allowed_targets(contract) == ("Borrador", "Terminado")
    with pytest.raises(LifecycleTransitionError, match="no puede quedar Vigente"):
        validate_contract_transition(contract, "Vigente")
    with pytest.raises(LifecycleTransitionError, match="Renovado"):
        validate_contract_transition(contract, "Renovado")
    with pytest.raises(LifecycleTransitionError, match="evidencia de firma"):
        ensure_contract_can_renew(NS(**vars(contract), status="Terminado"))

    unsigned_terminated = _unsigned_contract("Terminado")
    with pytest.raises(LifecycleTransitionError, match="evidencia de firma"):
        validate_contract_transition(unsigned_terminated, "Renovado", allow_renewal=True)


def test_v26012_signed_contract_can_suspend_resume_and_renew_but_not_return_to_draft() -> None:
    active = _signed_contract("Vigente")
    validate_contract_transition(active, "Suspendido")
    ensure_contract_can_renew(active)

    suspended = _signed_contract("Suspendido")
    validate_contract_transition(suspended, "Vigente")
    assert contract_allowed_targets(suspended) == ("Vigente", "Suspendido", "Terminado")

    with pytest.raises(LifecycleTransitionError):
        validate_contract_transition(active, "Borrador")


def test_v26012_contract_signing_is_single_handoff_from_draft() -> None:
    ensure_contract_can_sign(_unsigned_contract("Borrador"), has_snapshot=False)
    with pytest.raises(LifecycleTransitionError):
        ensure_contract_can_sign(_unsigned_contract("Suspendido"), has_snapshot=False)
    with pytest.raises(LifecycleTransitionError):
        ensure_contract_can_sign(_signed_contract("Borrador"), has_snapshot=False)
    with pytest.raises(LifecycleTransitionError):
        ensure_contract_can_sign(_unsigned_contract("Borrador"), has_snapshot=True)


def test_v26012_service_order_transition_matrix_prevents_timestamp_contradictions() -> None:
    planned = NS(status="Planeada", delivered_at=None)
    assert order_allowed_targets(planned) == ("Planeada", "En ejecución", "Bloqueada", "Cancelada")
    validate_order_transition(planned, "En ejecución")
    with pytest.raises(LifecycleTransitionError):
        validate_order_transition(planned, "Aceptada")

    delivered = NS(status="Entregada", delivered_at=datetime.now(UTC))
    assert order_allowed_targets(delivered) == ("En ejecución", "Entregada", "Aceptada")
    validate_order_transition(delivered, "En ejecución")
    validate_order_transition(delivered, "Aceptada")

    for terminal in ("Aceptada", "Cancelada"):
        item = NS(status=terminal, delivered_at=datetime.now(UTC))
        validate_order_transition(item, terminal)
        with pytest.raises(LifecycleTransitionError):
            validate_order_transition(item, "Planeada")


def test_v26012_invoice_payment_requires_authoritative_total_but_legacy_is_not_rewritten() -> None:
    known = NS(status="Pendiente", amount_semantics=INVOICE_TOTAL_WITH_TAX, total_amount=Decimal("119.00"))
    validate_invoice_transition(known, "Pagada")

    base = NS(status="Pendiente", amount_semantics=INVOICE_BASE_BEFORE_TAX, total_amount=None)
    with pytest.raises(LifecycleTransitionError, match="total económico conocido"):
        validate_invoice_transition(base, "Pagada")

    legacy = NS(status="Pendiente", amount_semantics=None, total_amount=None)
    with pytest.raises(LifecycleTransitionError, match="total económico conocido"):
        validate_invoice_transition(legacy, "Pagada")

    already_paid_legacy = NS(status="Pagada", amount_semantics=None, total_amount=None)
    validate_invoice_transition(already_paid_legacy, "Pagada")
    with pytest.raises(LifecycleTransitionError):
        validate_invoice_transition(already_paid_legacy, "Pendiente")


def test_v26012_billing_document_cannot_unemit_or_revive_an_annulled_record() -> None:
    emitted = NS(status="Emitido externamente")
    assert document_allowed_targets(emitted) == ("Emitido externamente", "Anulado")
    validate_document_transition(emitted, "Anulado")
    with pytest.raises(LifecycleTransitionError):
        validate_document_transition(emitted, "Pendiente de integración")

    annulled = NS(status="Anulado")
    assert document_allowed_targets(annulled) == ("Anulado",)
    with pytest.raises(LifecycleTransitionError):
        validate_document_transition(annulled, "Emitido externamente")


def test_v26012_collection_completion_is_one_time_and_requires_meaningful_result() -> None:
    pending = NS(status="Pendiente")
    assert ensure_collection_can_complete(pending, "  Cliente confirmó recepción.  ") == "Cliente confirmó recepción."
    with pytest.raises(LifecycleTransitionError, match="resultado"):
        ensure_collection_can_complete(pending, "   ")
    with pytest.raises(LifecycleTransitionError, match="ya fue completada"):
        ensure_collection_can_complete(NS(status="Completada"), "otro resultado")
