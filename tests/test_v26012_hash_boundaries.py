from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.commercial_lifecycle import LifecyclePersistenceConflict
from app.database import SessionLocal
from app.db.models import CommercialProposal, Organization, ServiceContract, ServiceOrder


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _organization_id() -> int:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        return organization.id


def _accepted_proposal() -> CommercialProposal:
    now = datetime.now(UTC)
    return CommercialProposal(
        reference=_uid("PROP-HASH"),
        public_token=_uid("TOKEN"),
        title="Propuesta con aceptación consolidada",
        company_name="Cliente evidencia V2.60.12",
        status="Aceptada",
        valid_until=date.today() + timedelta(days=30),
        billing_cycle="Anual",
        implementation_fee=Decimal("100.00"),
        recurring_fee=Decimal("200.00"),
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("19.0000"),
        first_year_total=Decimal("357.00"),
        scope_json='["Alcance firmado"]',
        deliverables_json='["Entregable firmado"]',
        terms="Condiciones aceptadas",
        contract_version="1.1",
        accepted_by="Cliente Firmante",
        accepted_email="cliente@example.com",
        accepted_ip="127.0.0.1",
        accepted_at=now,
        acceptance_hash="b" * 64,
        created_by="tests@calculatuhuella.local",
    )


def _signed_contract(*, status: str = "Vigente") -> ServiceContract:
    now = datetime.now(UTC)
    return ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-HASH"),
        title="Contrato con firma consolidada",
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
        terms_snapshot="Condiciones firmadas",
        signed_by="Firmante V2.60.12",
        signed_email="firma@example.com",
        signed_at=now,
        signature_hash="a" * 64,
        signature_version="1.1",
        signature_payload='{"signature_version":"1.1"}',
        signature_snapshot_created_at=now,
        created_by="tests@calculatuhuella.local",
    )


def test_v26012_acceptance_hash_freezes_every_bound_business_field() -> None:
    proposal = _accepted_proposal()
    with SessionLocal() as session:
        session.add(proposal)
        session.commit()
        proposal_id = proposal.id
        original_fee = proposal.recurring_fee
        original_terms = proposal.terms
        original_hash = proposal.acceptance_hash

        proposal.recurring_fee = Decimal("201.00")
        with pytest.raises(LifecyclePersistenceConflict, match="aceptación de propuesta"):
            session.commit()
        session.rollback()

        persisted = session.get(CommercialProposal, proposal_id)
        assert persisted is not None
        assert persisted.recurring_fee == original_fee
        assert persisted.terms == original_terms
        assert persisted.acceptance_hash == original_hash

        persisted.terms = "Condiciones reescritas"
        with pytest.raises(LifecyclePersistenceConflict, match="aceptación de propuesta"):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        persisted = session.get(CommercialProposal, proposal_id)
        assert persisted is not None
        assert persisted.recurring_fee == original_fee
        assert persisted.terms == original_terms
        assert persisted.acceptance_hash == original_hash


def test_v26012_signature_hash_freezes_contract_snapshot_fields_but_not_valid_status_flow() -> None:
    contract = _signed_contract(status="Vigente")
    with SessionLocal() as session:
        session.add(contract)
        session.commit()
        contract_id = contract.id
        original_value = contract.contract_value
        original_terms = contract.terms_snapshot
        original_hash = contract.signature_hash

        contract.contract_value = Decimal("1200.00")
        with pytest.raises(LifecyclePersistenceConflict, match="firma contractual"):
            session.commit()
        session.rollback()

        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None
        persisted.terms_snapshot = "Condiciones alteradas"
        with pytest.raises(LifecyclePersistenceConflict, match="firma contractual"):
            session.commit()
        session.rollback()

        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None
        persisted.status = "Suspendido"
        session.commit()
        assert persisted.status == "Suspendido"
        persisted.status = "Vigente"
        session.commit()
        assert persisted.status == "Vigente"

    with SessionLocal() as session:
        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None
        assert persisted.contract_value == original_value
        assert persisted.terms_snapshot == original_terms
        assert persisted.signature_hash == original_hash
        assert persisted.status == "Vigente"


def test_v26012_new_signature_cannot_be_injected_into_non_draft_contract() -> None:
    contract = ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-SUSPENDED-UNSIGNED"),
        title="Contrato suspendido sin firma",
        status="Suspendido",
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

        now = datetime.now(UTC)
        contract.signed_by = "Firma tardía"
        contract.signed_email = "firma@example.com"
        contract.signed_at = now
        contract.signature_hash = "c" * 64
        contract.signature_version = "1.1"
        contract.signature_payload = '{"late":true}'
        contract.signature_snapshot_created_at = now
        contract.status = "Vigente"
        with pytest.raises(LifecyclePersistenceConflict, match="solo puede originarse.*Borrador"):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        persisted = session.get(ServiceContract, contract_id)
        assert persisted is not None
        assert persisted.status == "Suspendido"
        assert not persisted.signature_hash
        assert persisted.signed_at is None


def test_v26012_legacy_unsigned_contract_renews_only_through_a_linked_child() -> None:
    parent = ServiceContract(
        organization_id=_organization_id(),
        reference=_uid("CTR-UNSIGNED-END"),
        title="Contrato terminado legacy sin firma",
        status="Terminado",
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),
        contract_value=Decimal("900.00"),
        billing_cycle="Anual",
        owner="Equipo comercial",
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(parent)
        session.commit()
        parent_id = parent.id

        parent.status = "Renovado"
        with pytest.raises(LifecyclePersistenceConflict, match="renovación contractual vinculada"):
            session.commit()
        session.rollback()

        parent = session.get(ServiceContract, parent_id)
        assert parent is not None and parent.status == "Terminado"
        child_reference = _uid("CTR-UNSIGNED-RENEWAL")
        parent.status = "Renovado"
        child = ServiceContract(
            organization_id=parent.organization_id,
            parent_contract_id=parent.id,
            reference=child_reference,
            title=parent.title,
            version="2.0",
            status="Borrador",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            contract_value=Decimal("1000.00"),
            billing_cycle="Anual",
            owner=parent.owner,
            created_by="tests@calculatuhuella.local",
        )
        session.add(child)
        session.commit()
        child_id = child.id
        assert parent.status == "Renovado"
        assert child.parent_contract_id == parent.id
        assert not parent.signature_hash

    with SessionLocal() as session:
        persisted_parent = session.get(ServiceContract, parent_id)
        persisted_child = session.get(ServiceContract, child_id)
        assert persisted_parent is not None and persisted_parent.status == "Renovado"
        assert persisted_child is not None and persisted_child.parent_contract_id == parent_id
        assert not persisted_parent.signature_hash


def test_v26012_order_acceptance_cannot_fabricate_delivery_in_same_flush() -> None:
    order = ServiceOrder(
        organization_id=_organization_id(),
        reference=_uid("OS-LEGACY-DELIVERY"),
        title="Orden entregada legacy sin timestamp",
        status="Entregada",
        delivered_at=None,
        created_by="tests@calculatuhuella.local",
    )
    with SessionLocal() as session:
        session.add(order)
        session.commit()
        order_id = order.id

        now = datetime.now(UTC)
        order.status = "Aceptada"
        order.delivered_at = now
        order.accepted_at = now
        with pytest.raises(LifecyclePersistenceConflict, match="persistida previamente"):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        persisted = session.get(ServiceOrder, order_id)
        assert persisted is not None
        assert persisted.status == "Entregada"
        assert persisted.delivered_at is None
        assert persisted.accepted_at is None
