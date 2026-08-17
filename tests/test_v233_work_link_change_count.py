from __future__ import annotations

from sqlalchemy import select

from app.database import AppUser, DataRequest, Inventory, SessionLocal, WorkItemLink
from app.workflow_bridge import sync_data_request


def test_v233_link_only_repair_is_reported_as_a_sync_change() -> None:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        request_record = session.scalar(
            select(DataRequest)
            .join(Inventory, Inventory.id == DataRequest.inventory_id)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(DataRequest.id)
        )
        assert request_record is not None

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
        origin.route = "/informacion"
        session.flush()

        repaired_item, changed = sync_data_request(
            session,
            request_record,
            organization_id=user.organization_id,
            actor_email=user.email,
        )
        session.flush()

        assert repaired_item.source_route == expected_route
        assert changed is True
        repaired_origin = session.scalar(
            select(WorkItemLink).where(
                WorkItemLink.work_item_id == repaired_item.id,
                WorkItemLink.entity_type == "DataRequest",
                WorkItemLink.entity_id == request_record.id,
                WorkItemLink.relationship_type == "origin",
            )
        )
        assert repaired_origin is not None
        assert repaired_origin.route == expected_route
        session.rollback()
