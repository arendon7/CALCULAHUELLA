from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, DataRequest, Inventory, SessionLocal, WorkItem, WorkItemLink
from app.main import app
from app.workflow_bridge import sync_data_request


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def representative_request(session: SessionLocal) -> tuple[AppUser, DataRequest]:
    user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
    assert user is not None
    request_record = session.scalar(
        select(DataRequest)
        .join(Inventory, Inventory.id == DataRequest.inventory_id)
        .where(Inventory.organization_id == user.organization_id)
        .order_by(DataRequest.id)
    )
    assert request_record is not None
    return user, request_record


def test_v232_sync_binds_item_and_origin_link_to_explicit_inventory_route() -> None:
    with SessionLocal() as session:
        user, request_record = representative_request(session)
        item, _ = sync_data_request(
            session,
            request_record,
            organization_id=user.organization_id,
            actor_email=user.email,
        )
        session.flush()
        expected_route = f"/inventarios/{request_record.inventory_id}"
        assert item.source_route == expected_route
        origin = session.scalar(
            select(WorkItemLink).where(
                WorkItemLink.work_item_id == item.id,
                WorkItemLink.entity_type == "DataRequest",
                WorkItemLink.entity_id == request_record.id,
                WorkItemLink.relationship_type == "origin",
            )
        )
        assert origin is not None
        assert origin.route == expected_route
        session.rollback()


def test_v232_work_queue_never_labels_a_data_request_link_as_generic_information_origin() -> None:
    with SessionLocal() as session:
        user, request_record = representative_request(session)
        request_id = request_record.id
        inventory_id = request_record.inventory_id

    with TestClient(app) as client:
        login(client)
        response = client.get("/mi-trabajo?scope=all")

    assert response.status_code == 200
    with SessionLocal() as session:
        item = session.scalar(
            select(WorkItem).where(
                WorkItem.source_entity_type == "DataRequest",
                WorkItem.source_entity_id == request_id,
            )
        )
        assert item is not None
        item_id = item.id
        assert item.source_route == f"/inventarios/{inventory_id}"

    soup = BeautifulSoup(response.text, "html.parser")
    card = soup.select_one(f"#tarea-{item_id}")
    assert card is not None
    link = card.select_one("a.work-source-link")
    assert link is not None
    assert link.get("href") == f"/inventarios/{inventory_id}"
    assert "Abrir expediente del periodo" in link.get_text(" ", strip=True)
