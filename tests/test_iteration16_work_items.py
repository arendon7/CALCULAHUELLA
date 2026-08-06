from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.access_control import ROLE_CAPABILITIES
from app.database import (
    AppUser,
    DataRequest,
    Inventory,
    OrganizationMembership,
    SessionLocal,
    WorkItem,
    WorkItemEvent,
)
from app.main import app
from app.product_experience import navigation_for
from app.workflow_bridge import sync_data_requests, transition_work_item
from app.workflow_service import create_work_item

pytestmark = pytest.mark.smoke


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


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


def test_iteration16_mi_trabajo_is_the_first_essential_entry_for_every_role() -> None:
    for role, capabilities in ROLE_CAPABILITIES.items():
        navigation = navigation_for({"role": role, "capabilities": capabilities}, "essential")
        labels = [item["label"] for section in navigation["core"] for item in section["items"]]
        assert labels[0] == "Mi trabajo"
        assert "Centro de trabajo" not in labels


def test_iteration16_data_request_sync_is_idempotent() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        organization_id = int(admin["organization_id"])
        request_count = session.scalar(
            select(func.count(DataRequest.id))
            .join(DataRequest.inventory)
            .where(DataRequest.inventory.has(organization_id=organization_id))
        ) or 0
        first = sync_data_requests(session, organization_id, str(admin["email"]))
        session.commit()
        work_count = session.scalar(
            select(func.count(WorkItem.id)).where(
                WorkItem.organization_id == organization_id,
                WorkItem.source_entity_type == "DataRequest",
            )
        ) or 0
        second = sync_data_requests(session, organization_id, str(admin["email"]))
        session.commit()

        assert first["total"] == request_count
        assert work_count == request_count
        assert second == {"total": request_count, "changed": 0}



def test_iteration16_synced_request_remains_visible_and_updates_its_source() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        organization_id = int(admin["organization_id"])
        client = _user_context(session, "Cliente", organization_id)
        request_record = session.scalar(
            select(DataRequest)
            .join(Inventory, Inventory.id == DataRequest.inventory_id)
            .where(
                Inventory.organization_id == organization_id,
                DataRequest.status == "Pendiente",
                ~DataRequest.requested_to.contains("@"),
            )
            .order_by(DataRequest.id)
        )
        assert request_record is not None
        sync_data_requests(session, organization_id, str(admin["email"]))
        item = session.scalar(
            select(WorkItem).where(
                WorkItem.organization_id == organization_id,
                WorkItem.source_entity_type == "DataRequest",
                WorkItem.source_entity_id == request_record.id,
            )
        )
        assert item is not None
        assert item.assignee_role == "Cliente"
        transition_work_item(
            session, item, client, action="accept_assignment", expected_version=item.version
        )
        session.commit()
        session.refresh(request_record)
        assert request_record.status == "En preparación"

def test_iteration16_work_item_completes_the_full_handoff_chain() -> None:
    with SessionLocal() as session:
        admin = _user_context(session, "Administrador")
        client = _user_context(session, "Cliente", int(admin["organization_id"]))
        item = create_work_item(
            session,
            admin,
            title="Entregar consumo de electricidad",
            work_type="data_request",
            assignee_email=str(client["email"]),
            acceptance_criteria="Doce periodos, unidad kWh y factura relacionada.",
        )
        session.flush()
        assert item.status_code == "assigned"

        transition_work_item(session, item, client, action="accept_assignment", expected_version=item.version)
        transition_work_item(session, item, client, action="start", expected_version=item.version)
        transition_work_item(session, item, client, action="submit", comment="Datos y facturas cargados.", expected_version=item.version)
        transition_work_item(session, item, admin, action="start_validation", expected_version=item.version)
        transition_work_item(session, item, admin, action="send_to_review", expected_version=item.version)
        transition_work_item(session, item, admin, action="accept_delivery", comment="Cobertura y soportes conformes.", expected_version=item.version)
        transition_work_item(session, item, admin, action="close", expected_version=item.version)
        session.commit()

        assert item.status_code == "closed"
        assert item.accepted_at is not None
        assert item.submitted_at is not None
        assert item.reviewed_at is not None
        assert item.approved_at is not None
        assert item.closed_at is not None
        event_count = session.scalar(
            select(func.count(WorkItemEvent.id)).where(WorkItemEvent.work_item_id == item.id)
        )
        assert event_count == 8


def test_iteration16_mi_trabajo_route_and_api_are_available() -> None:
    with TestClient(app) as client:
        login(client)
        page = client.get("/mi-trabajo?scope=all")
        assert page.status_code == 200
        assert "Mi trabajo" in page.text
        assert "Entregar no es cerrar" in page.text
        assert "Crear trabajo controlado" in page.text

        payload = client.get("/api/mi-trabajo?scope=all")
        assert payload.status_code == 200
        data = payload.json()
        assert data["scope"] == "all"
        assert {"open", "overdue", "returned", "blocked", "under_review"} <= set(data["summary"])
        assert isinstance(data["items"], list)
