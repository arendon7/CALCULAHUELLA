from __future__ import annotations

from datetime import date

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.access_control import ROLE_CAPABILITIES
from app.database import (
    AppUser,
    Inventory,
    Notification,
    OrganizationMembership,
    PeriodClose,
    ReductionAction,
    ReportArtifact,
    SessionLocal,
    WorkItem,
)
from app.main import app
from app.workflow_bridge import create_work_item, sync_data_requests, transition_work_item
from app.workflow_stabilization import source_status_should_override
from app.workflow_service import WorkflowServiceError, visible_work_items

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


def _two_admin_contexts(session) -> tuple[dict[str, object], dict[str, object]]:
    memberships = list(
        session.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.role == "Administrador", OrganizationMembership.active.is_(True))
            .order_by(OrganizationMembership.organization_id, OrganizationMembership.id)
        )
    )
    by_org: dict[int, OrganizationMembership] = {}
    for membership in memberships:
        by_org.setdefault(membership.organization_id, membership)
    assert len(by_org) >= 2
    contexts: list[dict[str, object]] = []
    for membership in list(by_org.values())[:2]:
        db_user = session.get(AppUser, membership.user_id)
        assert db_user is not None
        contexts.append(
            {
                "id": db_user.id,
                "organization_id": membership.organization_id,
                "email": db_user.email,
                "role": membership.role,
                "capabilities": ROLE_CAPABILITIES[membership.role],
            }
        )
    return contexts[0], contexts[1]


def _login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_iteration18_source_sync_never_regresses_coarse_states() -> None:
    assert source_status_should_override("under_review", "accepted_by_reviewer")
    assert not source_status_should_override("accepted_by_reviewer", "under_review")
    assert not source_status_should_override("closed", "accepted_by_reviewer")
    assert source_status_should_override("closed", "returned")
    assert source_status_should_override("in_progress", "blocked")
    assert source_status_should_override("returned", "in_progress")


def test_iteration18_specialized_sync_preserves_review_acceptance() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        organization_id = int(admin["organization_id"])
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == organization_id)
            .order_by(Inventory.id)
        )
        assert inventory is not None

        close = session.scalar(
            select(PeriodClose)
            .where(PeriodClose.organization_id == organization_id)
            .order_by(PeriodClose.id)
        )
        if close is None:
            close = PeriodClose(
                organization_id=organization_id,
                inventory_id=inventory.id,
                period_start=inventory.start_date,
                period_end=inventory.start_date,
                status="En revisión",
            )
            session.add(close)
            session.flush()
        else:
            close.status = "En revisión"

        action = session.scalar(
            select(ReductionAction)
            .join(Inventory, Inventory.id == ReductionAction.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(ReductionAction.id)
        )
        if action is None:
            action = ReductionAction(
                inventory_id=inventory.id,
                title="Acción de reducción de prueba",
                status="En seguimiento",
                responsible="Cliente",
                created_by=str(admin["email"]),
            )
            session.add(action)
            session.flush()
        else:
            action.status = "En seguimiento"

        report = session.scalar(
            select(ReportArtifact)
            .join(Inventory, Inventory.id == ReportArtifact.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(ReportArtifact.id)
        )
        if report is None:
            report = ReportArtifact(
                inventory_id=inventory.id,
                report_type="Inventario corporativo",
                status="Aprobado",
                file_name="reporte-prueba.pdf",
                stored_name="reporte-prueba.pdf",
                generated_by=str(admin["email"]),
                approved_by=str(admin["email"]),
            )
            session.add(report)
            session.flush()
        else:
            report.status = "Aprobado"
        session.commit()

        sync_data_requests(session, organization_id, str(admin["email"]))
        session.commit()

        for entity_type, entity_id in (
            ("PeriodClose", close.id),
            ("ReductionAction", action.id),
            ("ReportArtifact", report.id),
        ):
            item = session.scalar(
                select(WorkItem).where(
                    WorkItem.organization_id == organization_id,
                    WorkItem.source_entity_type == entity_type,
                    WorkItem.source_entity_id == entity_id,
                )
            )
            assert item is not None
            item.status_code = "accepted_by_reviewer"
            item.next_action = "Cerrar la tarea y actualizar el registro relacionado."
        session.commit()

        sync_data_requests(session, organization_id, str(admin["email"]))
        session.commit()

        for entity_type, entity_id in (
            ("PeriodClose", close.id),
            ("ReductionAction", action.id),
            ("ReportArtifact", report.id),
        ):
            preserved = session.scalar(
                select(WorkItem).where(
                    WorkItem.organization_id == organization_id,
                    WorkItem.source_entity_type == entity_type,
                    WorkItem.source_entity_id == entity_id,
                )
            )
            assert preserved is not None
            assert preserved.status_code == "accepted_by_reviewer"


def test_iteration18_work_items_are_isolated_by_organization() -> None:
    with SessionLocal() as session:
        admin_one, admin_two = _two_admin_contexts(session)
        item = create_work_item(
            session,
            admin_one,
            title="Tarea aislada de la organización uno",
            work_type="data_request",
            assignee_role="Cliente",
            acceptance_criteria="Entregar un registro con evidencia suficiente.",
        )
        session.commit()

        other_items = visible_work_items(session, admin_two, scope="all")
        assert item.id not in {row.id for row in other_items}
        with pytest.raises(WorkflowServiceError, match="organización activa"):
            transition_work_item(
                session,
                item,
                admin_two,
                action="accept_assignment",
                expected_version=item.version,
            )


def test_iteration18_notifications_do_not_target_the_actor() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        before = session.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == int(admin["organization_id"]),
                Notification.user_id == int(admin["id"]),
            )
        ) or 0
        item = create_work_item(
            session,
            admin,
            title="Tarea asignada al mismo administrador",
            work_type="integration_exception",
            assignee_email=str(admin["email"]),
            acceptance_criteria="Documentar causa, corrección y evidencia de cierre.",
        )
        transition_work_item(
            session,
            item,
            admin,
            action="accept_assignment",
            expected_version=item.version,
        )
        session.commit()
        after = session.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == int(admin["organization_id"]),
                Notification.user_id == int(admin["id"]),
            )
        ) or 0
        assert after == before


def test_iteration18_mi_trabajo_has_accessible_controls_and_mobile_contract() -> None:
    with TestClient(app) as client:
        _login(client)
        response = client.get("/mi-trabajo?scope=all")
        assert response.status_code == 200
        soup = BeautifulSoup(response.text, "html.parser")

        assert soup.find("h1", string="Mi trabajo") is not None
        assert soup.select_one('section[aria-label="Resumen de trabajo"]') is not None
        assert "@media(max-width:640px)" in response.text
        assert "grid-template-columns:1fr" in response.text

        unnamed: list[str] = []
        for control in soup.select("input:not([type=hidden]), select, textarea"):
            has_label = control.find_parent("label") is not None
            has_name = bool(control.get("aria-label") or control.get("aria-labelledby"))
            has_hint = bool(control.get("placeholder") or control.get("title"))
            if not (has_label or has_name or has_hint):
                unnamed.append(str(control)[:120])
        assert unnamed == []

        for button in soup.select("button"):
            assert button.get_text(" ", strip=True) or button.get("aria-label")


def test_iteration18_api_never_exposes_another_organization() -> None:
    with SessionLocal() as session:
        admin_one, admin_two = _two_admin_contexts(session)
        foreign = create_work_item(
            session,
            admin_two,
            title="No debe aparecer en la organización uno",
            work_type="data_request",
            assignee_role="Cliente",
            acceptance_criteria="Registro segregado por organización.",
        )
        session.commit()
        foreign_id = foreign.id
        email_one = str(admin_one["email"])

    with TestClient(app) as client:
        _login(client, email_one)
        response = client.get("/api/mi-trabajo?scope=all")
        assert response.status_code == 200
        ids = {row["id"] for row in response.json()["items"]}
        assert foreign_id not in ids
