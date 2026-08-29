from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.commercial_lifecycle import (
    LifecyclePersistenceConflict,
    LifecycleTransitionError,
    contract_allowed_targets,
    ensure_contract_can_renew,
    ensure_contract_can_sign,
    ensure_proposal_can_decide,
    ensure_proposal_can_send,
    normalize_payment_provider_status,
    validate_contract_transition,
    validate_invoice_transition,
    validate_order_transition,
    validate_payment_transition,
)
from app.database import SessionLocal
from app.db.models import (
    BillingDocumentRecord,
    BillingInvoice,
    CollectionAction,
    CommercialProposal,
    Organization,
    PaymentTransaction,
    ServiceContract,
    ServiceOrder,
)
from app.main import app
from app.revenue_operations import INVOICE_BASE_BEFORE_TAX, INVOICE_TOTAL_WITH_TAX


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _organization_id() -> int:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        return organization.id


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _signed_contract(*, status: str = "Vigente") -> ServiceContract:
    now = datetime.now(UTC)
    return ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-V26012"),
        title="Contrato lifecycle V2.60.12",
        version="1.0",
        status=status,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        renewal_type="Anual",
        auto_renew=False,
        notice_days=30,
        contract_value=Decimal("1000.00"),
        billing_cycle="Anual",
        owner="Equipo comercial",
        terms_snapshot="Condiciones congeladas",
        signed_by="Firmante V2.60.12",
        signed_email="firma@example.com",
        signed_at=now,
        signature_hash="a" * 64,
        signature_version="1.1",
        signature_payload='{"v":"1.1"}',
        signature_snapshot_created_at=now,
        created_by="tests@calculatuhuella.local",
    )


def test_v26012_policy_preserves_open_proposal_compatibility_and_terminal_evidence() -> None:
    draft = SimpleNamespace(status="Borrador", acceptance_hash="", accepted_at=None)
    ensure_proposal_can_send(draft)
    ensure_proposal_can_decide(draft, action="aceptación")

    accepted = SimpleNamespace(status="Aceptada", acceptance_hash="abc", accepted_at=datetime.now(UTC))
    with pytest.raises(LifecycleTransitionError):
        ensure_proposal_can_send(accepted)
    with pytest.raises(LifecycleTransitionError):
        ensure_proposal_can_decide(accepted, action="rechazo")


def test_v26012_payment_provider_is_closed_and_terminal_regression_is_forbidden() -> None:
    assert normalize_payment_provider_status("APPROVED") == "Pagada"
    assert normalize_payment_provider_status("refunded") == "Reembolsada"
    with pytest.raises(LifecycleTransitionError):
        normalize_payment_provider_status("chargeback_magic")
    validate_payment_transition("Pendiente", "Pagada")
    validate_payment_transition("Pagada", "Reembolsada")
    with pytest.raises(LifecycleTransitionError):
        validate_payment_transition("Pagada", "Pendiente")


def test_v26012_contract_policy_requires_signature_for_vigente_and_versioned_renewal() -> None:
    unsigned = SimpleNamespace(
        status="Borrador", signature_hash="", signed_at=None, signed_by="", signed_email=""
    )
    assert "Vigente" not in contract_allowed_targets(unsigned)
    with pytest.raises(LifecycleTransitionError):
        validate_contract_transition(unsigned, "Vigente")
    ensure_contract_can_sign(unsigned)

    signed_suspended = SimpleNamespace(
        status="Suspendido",
        signature_hash="a" * 64,
        signed_at=datetime.now(UTC),
        signed_by="Laura",
        signed_email="laura@example.com",
    )
    validate_contract_transition(signed_suspended, "Vigente")
    with pytest.raises(LifecycleTransitionError):
        validate_contract_transition(signed_suspended, "Renovado")

    signed_active = SimpleNamespace(**{**signed_suspended.__dict__, "status": "Vigente"})
    ensure_contract_can_renew(signed_active)
    legacy_unsigned_active = SimpleNamespace(
        status="Vigente", signature_hash="", signed_at=None, signed_by="", signed_email=""
    )
    ensure_contract_can_renew(legacy_unsigned_active)


def test_v26012_order_and_invoice_policy_rejects_factless_terminal_states() -> None:
    planned = SimpleNamespace(status="Planeada", delivered_at=None)
    with pytest.raises(LifecycleTransitionError):
        validate_order_transition(planned, "Aceptada")

    delivered = SimpleNamespace(status="Entregada", delivered_at=datetime.now(UTC))
    validate_order_transition(delivered, "Aceptada")

    base_invoice = SimpleNamespace(
        status="Vencida", amount_semantics=INVOICE_BASE_BEFORE_TAX, total_amount=None
    )
    with pytest.raises(LifecycleTransitionError):
        validate_invoice_transition(base_invoice, "Pagada")

    total_invoice = SimpleNamespace(
        status="Vencida", amount_semantics=INVOICE_TOTAL_WITH_TAX, total_amount=Decimal("119.00")
    )
    validate_invoice_transition(total_invoice, "Pagada")


def test_v26012_orm_blocks_manual_unsigned_contract_activation_without_persisting() -> None:
    contract = ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-UNSIGNED"),
        title="Contrato no firmado",
        status="Borrador",
        start_date=date.today(),
        contract_value=Decimal("1000.00"),
        billing_cycle="Anual",
        owner="Equipo comercial",
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(contract)
        session.commit()
        contract_id = contract.id
        contract.status = "Vigente"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None
        assert persisted.status == "Borrador"
        assert not persisted.signature_hash


def test_v26012_http_manual_unsigned_contract_activation_returns_409() -> None:
    contract = ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-HTTP-UNSIGNED"),
        title="Contrato HTTP no firmado",
        status="Borrador",
        start_date=date.today(),
        contract_value=Decimal("1000.00"),
        billing_cycle="Anual",
        owner="Equipo comercial",
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(contract)
        session.commit()
        contract_id = contract.id

    with TestClient(app) as client:
        _login(client)
        response = client.post(
            f"/operacion-comercial/contratos/{contract_id}/estado",
            data={"status": "Vigente"},
            follow_redirects=False,
        )
        assert response.status_code == 409

    with SessionLocal() as session:
        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None and persisted.status == "Borrador"


def test_v26012_signed_suspended_contract_can_reactivate_but_manual_renewed_is_blocked() -> None:
    contract = _signed_contract(status="Suspendido")
    with SessionLocal() as session:
        session.add(contract)
        session.commit()
        contract_id = contract.id
        contract.status = "Vigente"
        session.commit()
        assert contract.status == "Vigente"
        contract.status = "Renovado"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None and persisted.status == "Vigente"


def test_v26012_renewal_child_is_the_only_authority_for_renovado() -> None:
    parent = _signed_contract(status="Vigente")
    with SessionLocal() as session:
        session.add(parent)
        session.commit()
        parent.status = "Renovado"
        child = ServiceContract(
            organization_id=parent.organization_id,
            parent_contract_id=parent.id,
            reference=_uid("CTR-RENEWAL"),
            title=parent.title,
            version="2.0",
            status="Borrador",
            start_date=date.today() + timedelta(days=366),
            end_date=date.today() + timedelta(days=730),
            renewal_type=parent.renewal_type,
            auto_renew=parent.auto_renew,
            notice_days=parent.notice_days,
            contract_value=Decimal("1200.00"),
            billing_cycle=parent.billing_cycle,
            owner=parent.owner,
            terms_snapshot=parent.terms_snapshot,
            created_by="tests@calculatuhuella.local",
        )
        session.add(child)
        session.commit()
        assert parent.status == "Renovado"
        assert child.parent_contract_id == parent.id


def test_v26012_order_terminal_state_cannot_regress_and_timestamps_are_first_write_only() -> None:
    now = datetime.now(UTC)
    order = ServiceOrder(
        organization_id=_organization_id(),
        reference=_uid("OS-V26012"),
        title="Orden aceptada",
        status="Aceptada",
        delivered_at=now,
        accepted_at=now,
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(order)
        session.commit()
        order_id = order.id
        order.status = "En ejecución"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(ServiceOrder, order_id)
        assert persisted is not None
        original_accepted_at = persisted.accepted_at
        persisted.accepted_at = datetime.now(UTC) + timedelta(minutes=1)
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(ServiceOrder, order_id)
        assert persisted.status == "Aceptada"
        assert persisted.accepted_at == original_accepted_at


def test_v26012_base_before_tax_invoice_cannot_be_marked_paid() -> None:
    invoice = BillingInvoice(
        organization_id=_organization_id(),
        reference=_uid("INV-BASE"),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("100.00"),
        status="Vencida",
        issued_at=date.today(),
        due_date=date.today(),
        charge_type="Recurrente",
        amount_semantics=INVOICE_BASE_BEFORE_TAX,
        net_amount=Decimal("100.00"),
        total_amount=None,
    )
    with SessionLocal() as session:
        session.add(invoice)
        session.commit()
        invoice_id = invoice.id
        invoice.status = "Pagada"
        invoice.paid_at = datetime.now(UTC)
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(BillingInvoice, invoice_id)
        assert persisted is not None
        assert persisted.status == "Vencida"
        assert persisted.paid_at is None


def test_v26012_emitted_document_preserves_external_evidence_and_cannot_regress() -> None:
    invoice = BillingInvoice(
        organization_id=_organization_id(),
        reference=_uid("INV-DOC"),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("119.00"),
        status="Pendiente",
        issued_at=date.today(),
        amount_semantics=INVOICE_TOTAL_WITH_TAX,
        net_amount=Decimal("100.00"),
        tax_rate_snapshot=Decimal("19.0000"),
        tax_amount=Decimal("19.00"),
        total_amount=Decimal("119.00"),
    )
    with SessionLocal() as session:
        session.add(invoice)
        session.flush()
        document = BillingDocumentRecord(
            organization_id=invoice.organization_id,
            invoice_id=invoice.id,
            document_type="Factura electrónica",
            internal_reference=_uid("DOC-V26012"),
            provider="Proveedor autorizado",
            external_number=_uid("FE"),
            status="Emitido externamente",
            issued_at=date.today(),
            cufe="cufe-v26012",
            document_url="https://example.com/documento",
            created_by="tests@calculatuhuella.local",
        )
        session.add(document)
        session.commit()
        document_id = document.id
        original_number = document.external_number
        document.status = "Pendiente de integración"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        document = session.get(BillingDocumentRecord, document_id)
        document.external_number = "REWRITTEN"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(BillingDocumentRecord, document_id)
        assert persisted.status == "Emitido externamente"
        assert persisted.external_number == original_number


def test_v26012_completed_collection_result_is_immutable() -> None:
    invoice = BillingInvoice(
        organization_id=_organization_id(),
        reference=_uid("INV-COL"),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("119.00"),
        status="Pendiente",
        issued_at=date.today(),
        amount_semantics=INVOICE_TOTAL_WITH_TAX,
        net_amount=Decimal("100.00"),
        tax_rate_snapshot=Decimal("19.0000"),
        tax_amount=Decimal("19.00"),
        total_amount=Decimal("119.00"),
    )
    with SessionLocal() as session:
        session.add(invoice)
        session.flush()
        action = CollectionAction(
            organization_id=invoice.organization_id,
            invoice_id=invoice.id,
            action_type="Recordatorio",
            status="Pendiente",
            created_by="tests@calculatuhuella.local",
        )
        session.add(action)
        session.commit()
        action_id = action.id
        action.status = "Completada"
        action.result = "Cliente confirmó recepción"
        action.completed_at = datetime.now(UTC)
        session.commit()
        first_result = action.result
        action.result = "Resultado reescrito"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(CollectionAction, action_id)
        assert persisted.status == "Completada"
        assert persisted.result == first_result


def test_v26012_accepted_proposal_cannot_be_rejected_again_over_public_route() -> None:
    now = datetime.now(UTC)
    proposal = CommercialProposal(
        reference=_uid("PROP-TERMINAL"),
        public_token=_uid("TOKEN"),
        title="Propuesta ya aceptada",
        company_name="Cliente V2.60.12",
        status="Aceptada",
        valid_until=date.today() + timedelta(days=30),
        billing_cycle="Anual",
        implementation_fee=Decimal("100.00"),
        recurring_fee=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("19.0000"),
        first_year_total=Decimal("238.00"),
        scope_json='["Alcance"]',
        deliverables_json='["Entrega"]',
        terms="Condiciones",
        contract_version="1.1",
        accepted_by="Cliente",
        accepted_email="cliente@example.com",
        accepted_ip="127.0.0.1",
        accepted_at=now,
        acceptance_hash="b" * 64,
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(proposal)
        session.commit()
        proposal_id = proposal.id
        token = proposal.public_token
        original_hash = proposal.acceptance_hash
        original_accepted_at = proposal.accepted_at

    with TestClient(app) as client:
        response = client.post(
            f"/propuesta/{token}/rechazar",
            data={"reason": "Intento tardío"},
            follow_redirects=False,
        )
        assert response.status_code == 409

    with SessionLocal() as session:
        persisted = session.get(CommercialProposal, proposal_id)
        assert persisted.status == "Aceptada"
        assert persisted.acceptance_hash == original_hash
        assert persisted.accepted_at == original_accepted_at.replace(tzinfo=None) or persisted.accepted_at == original_accepted_at


def test_v26012_paid_transaction_cannot_regress_or_rewrite_paid_at() -> None:
    paid_at = datetime.now(UTC)
    payment = PaymentTransaction(
        public_token=_uid("PAY-TOKEN"),
        gateway="Demo",
        status="Pagada",
        amount=Decimal("119.00"),
        currency="COP",
        external_reference=_uid("PAY-EXT"),
        paid_at=paid_at,
    )
    with SessionLocal() as session:
        session.add(payment)
        session.commit()
        payment_id = payment.id
        payment.status = "Pendiente"
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        payment = session.get(PaymentTransaction, payment_id)
        payment.paid_at = datetime.now(UTC) + timedelta(minutes=5)
        with pytest.raises(LifecyclePersistenceConflict):
            session.commit()
        session.rollback()
        persisted = session.get(PaymentTransaction, payment_id)
        assert persisted.status == "Pagada"
        assert persisted.paid_at == paid_at.replace(tzinfo=None) or persisted.paid_at == paid_at
