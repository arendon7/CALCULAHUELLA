from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.db.models import Organization, ServiceContract
from app.monetary import MONEY_PORTABLE_MAX


def _contract(organization_id: int, reference: str, value: Decimal) -> ServiceContract:
    return ServiceContract(
        organization_id=organization_id,
        reference=reference,
        title="Contrato guard V2.60.9",
        version="1.0",
        status="Borrador",
        start_date=date(2026, 9, 1),
        renewal_type="Por acuerdo",
        auto_renew=False,
        notice_days=30,
        contract_value=value,
        billing_cycle="Anual",
        owner="CI",
        terms_snapshot="Prueba before_flush V2.60.9",
        created_by="ci@calculatuhuella.local",
    )


def test_v2609_before_flush_rejects_new_overlimit_authority_before_sql() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        contract = _contract(
            organization.id,
            "CTR-V2609-FLUSH-OVER",
            MONEY_PORTABLE_MAX + Decimal("0.01"),
        )
        session.add(contract)
        with pytest.raises(ValueError, match="límite portable"):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        assert session.scalar(
            select(ServiceContract).where(ServiceContract.reference == "CTR-V2609-FLUSH-OVER")
        ) is None


def test_v2609_before_flush_quantizes_changed_money_before_driver() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        contract = _contract(organization.id, "CTR-V2609-FLUSH-ROUND", Decimal("100.005"))
        session.add(contract)
        session.flush()
        assert contract.contract_value == Decimal("100.01")
        session.rollback()


def test_v2609_unrelated_update_does_not_reassign_unchanged_monetary_attribute() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        contract = _contract(organization.id, "CTR-V2609-FLUSH-HISTORY", Decimal("125.00"))
        session.add(contract)
        session.commit()
        contract_id = contract.id

    with SessionLocal() as session:
        contract = session.get(ServiceContract, contract_id)
        assert contract is not None
        original_value = contract.contract_value
        contract.owner = "Equipo actualizado"
        session.flush()
        assert contract.contract_value == original_value
        history = __import__("sqlalchemy").inspect(contract).attrs.contract_value.history
        assert not history.has_changes()
        session.rollback()
