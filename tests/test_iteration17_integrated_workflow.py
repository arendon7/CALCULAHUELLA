from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.access_control import ROLE_CAPABILITIES
from app.database import (
    AppUser,
    DataImportBatch,
    DataQualityFinding,
    Inventory,
    Notification,
    OrganizationMembership,
    PeriodClose,
    ReductionAction,
    ReportArtifact,
    ReviewObservation,
    SessionLocal,
    SupportMessage,
    SupportTicket,
    WorkItem,
)
from app.workflow_bridge import create_work_item, sync_data_requests
from app.workflow_integrations import mirror_source_from_work_item, sync_specialized_work_items

pytestmark = pytest.mark.smoke


def _user_context(session, role: str, organization_id: int | None = None) -> dict[str, object]:
    query = (
        select(OrganizationMembership)
        .where(OrganizationMembership.role == role, OrganizationMembership.active.is_(True))
        .order_by(OrganizationMembership.id)
    )
    if organization_id is not None:
        query = query.where(OrganizationMembership.organization_id == organization_id)
    membership = session.scalar(query)
    assert membership is not None
    db_user = session.get(AppUser, membership.user_id)
    assert db_user is not None
    return {
        "id": db_user.id,
        "organization_id": membership.organization_id,
        "email": db_user.email,
        "role": membership.role,
        "capabilities": ROLE_CAPABILITIES[membership.role],
    }


def _create_specialized_records(session, organization_id: int, inventory_id: int):
    observation = ReviewObservation(
        inventory_id=inventory_id,
        title="Factura sin periodo legible",
        description="La evidencia no permite confirmar el mes del consumo.",
        severity="Mayor",
        status="Abierta",
        assigned_to="Contabilidad",
        due_date=date(2035, 2, 10),
        created_by="revisor@calculatuhuella.local",
    )
    batch = DataImportBatch(
        organization_id=organization_id,
        inventory_id=inventory_id,
        code="ITER17-BATCH",
        filename="iter17.xlsx",
        file_hash="a" * 64,
        status="Validado",
    )
    session.add_all([observation, batch])
    session.flush()
    finding = DataQualityFinding(
        batch_id=batch.id,
        rule_code="UNIT_MISMATCH",
        severity="Error",
        message="La unidad declarada no coincide con la fuente.",
        status="Abierto",
    )
    close = PeriodClose(
        organization_id=organization_id,
        inventory_id=inventory_id,
        period_start=date(2035, 1, 1),
        period_end=date(2035, 1, 31),
        status="Abierto",
        expected_sources=1,
        ready_sources=0,
        blocked_sources=1,
        data_coverage_percent=50,
        evidence_coverage_percent=0,
        quality_score=40,
    )
    report = ReportArtifact(
        inventory_id=inventory_id,
        report_type="Informe ejecutivo",
        version="17.0",
        status="Generado",
        file_name="informe_iter17.pdf",
        stored_name="reports/informe_iter17.pdf",
        generated_by="consultor@calculatuhuella.local",
    )
    reduction = ReductionAction(
        inventory_id=inventory_id,
        title="Optimizar consumo eléctrico",
        description="Implementar control operativo y seguimiento mensual.",
        priority="Alta",
        responsible="Operaciones",
        target_date=date(2035, 6, 30),
        status="Identificada",
        created_by="consultor@calculatuhuella.local",
    )
    ticket = SupportTicket(
        organization_id=organization_id,
        inventory_id=inventory_id,
        created_by="cliente@calculatuhuella.local",
        request_type="Aclaración",
        category="Dato y evidencia",
        priority="Alta",
        status="Abierto",
        subject="Confirmar criterio de evidencia",
        description="Se requiere aclarar qué soporte es suficiente.",
        desired_outcome="Confirmar el soporte y registrar la decisión.",
        assigned_to="Consultor",
        due_date=date(2035, 2, 5),
    )
    session.add_all([finding, close, report, reduction, ticket])
    session.flush()
    return {
        "ReviewObservation": observation,
        "DataQualityFinding": finding,
        "PeriodClose": close,
        "ReportArtifact": report,
        "ReductionAction": reduction,
        "SupportTicket": ticket,
    }


def test_iteration17_specialized_sources_are_idempotent_and_visible_as_work() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        organization_id = int(admin["organization_id"])
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == organization_id)
            .order_by(Inventory.id)
        )
        assert inventory is not None
        _create_specialized_records(session, organization_id, inventory.id)

        first = sync_specialized_work_items(session, organization_id, str(admin["email"]))
        session.commit()
        second = sync_specialized_work_items(session, organization_id, str(admin["email"]))
        session.commit()

        assert first["changed"] >= 6
        assert second["changed"] == 0
        entity_types = set(
            session.scalars(
                select(WorkItem.source_entity_type).where(
                    WorkItem.organization_id == organization_id,
                    WorkItem.source_entity_type.in_(
                        [
                            "ReviewObservation",
                            "DataQualityFinding",
                            "PeriodClose",
                            "ReportArtifact",
                            "ReductionAction",
                            "SupportTicket",
                        ]
                    ),
                )
            )
        )
        assert entity_types == {
            "ReviewObservation",
            "DataQualityFinding",
            "PeriodClose",
            "ReportArtifact",
            "ReductionAction",
            "SupportTicket",
        }


def test_iteration17_work_state_is_mirrored_to_every_specialized_source() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        organization_id = int(admin["organization_id"])
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == organization_id)
            .order_by(Inventory.id)
        )
        assert inventory is not None
        records = _create_specialized_records(session, organization_id, inventory.id)
        sync_specialized_work_items(session, organization_id, str(admin["email"]))
        session.flush()

        items = {
            item.source_entity_type: item
            for item in session.scalars(
                select(WorkItem).where(
                    WorkItem.organization_id == organization_id,
                    WorkItem.source_entity_type.in_(list(records)),
                )
            )
        }
        for source_type, item in items.items():
            item.status_code = "closed" if source_type != "PeriodClose" else "returned"
            mirror_source_from_work_item(
                session,
                item,
                actor_email=str(admin["email"]),
                actor_role=str(admin["role"]),
                comment="Decisión documentada en Mi trabajo.",
            )
        session.commit()

        assert records["ReviewObservation"].status == "Cerrada"
        assert records["DataQualityFinding"].status == "Resuelto"
        assert records["PeriodClose"].status == "Reabierto"
        assert records["ReportArtifact"].status == "Aprobado"
        assert records["ReductionAction"].status == "Implementada"
        assert records["ReductionAction"].progress_percent == 100
        assert records["SupportTicket"].status == "Cerrado"
        assert session.scalar(
            select(func.count(SupportMessage.id)).where(
                SupportMessage.ticket_id == records["SupportTicket"].id
            )
        ) == 1


def test_iteration17_assignment_creates_a_notification_for_the_next_actor() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        client = _user_context(session, "Cliente", int(admin["organization_id"]))
        before = session.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == int(admin["organization_id"]),
                Notification.user_id == int(client["id"]),
            )
        ) or 0
        item = create_work_item(
            session,
            admin,
            title="Aportar evidencia de combustible",
            work_type="evidence_request",
            assignee_email=str(client["email"]),
            acceptance_criteria="Documento legible, periodo y fuente relacionados.",
        )
        session.commit()
        after = session.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == int(admin["organization_id"]),
                Notification.user_id == int(client["id"]),
            )
        ) or 0
        assert item.assignee_user_id == int(client["id"])
        assert after == before + 1


def test_iteration17_existing_sync_contract_is_preserved() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        result = sync_data_requests(
            session,
            int(admin["organization_id"]),
            str(admin["email"]),
        )
        session.commit()
        assert set(result) == {"total", "changed"}
        assert result["total"] >= 0
        assert result["changed"] >= 0
