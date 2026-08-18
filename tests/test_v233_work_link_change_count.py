from __future__ import annotations

import pytest
from sqlalchemy import select

from app.database import AppUser, DataRequest, Inventory, SessionLocal, WorkItemLink
from app.workflow_bridge import sync_data_request as sync_data_request_bridge
from app.workflow_service import sync_data_request as sync_data_request_service


@pytest.mark.smoke
def test_v233_link_only_repair_is_reported_as_a_sync_change() -> None:
    """A persisted stale origin link must be repaired and counted by service and bridge."""
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

        item, _ = sync_data_request_bridge(
            session,
            request_record,
            organization_id=user.organization_id,
            actor_email=user.email,
        )
        session.commit()

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

        organization_id = user.organization_id
        actor_email = user.email
        request_id = request_record.id
        item_id = item.id
        origin_id = origin.id

    def persist_stale_origin() -> None:
        with SessionLocal() as session:
            origin = session.get(WorkItemLink, origin_id)
            assert origin is not None
            origin.route = "/informacion"
            session.commit()

    # First prove the domain service itself repairs and counts a stale persisted link.
    persist_stale_origin()
    with SessionLocal() as session:
        request_record = session.get(DataRequest, request_id)
        stale_origin = session.get(WorkItemLink, origin_id)
        assert request_record is not None
        assert stale_origin is not None
        assert stale_origin.work_item_id == item_id
        assert stale_origin.route == "/informacion"

        repaired_item, service_changed = sync_data_request_service(
            session,
            request_record,
            organization_id=organization_id,
            actor_email=actor_email,
        )
        session.flush()

        assert repaired_item.source_route == expected_route
        assert stale_origin.route == expected_route
        assert service_changed is True
        session.commit()

    # Then prove the compatibility bridge preserves that changed signal as well.
    persist_stale_origin()
    with SessionLocal() as session:
        request_record = session.get(DataRequest, request_id)
        stale_origin = session.get(WorkItemLink, origin_id)
        assert request_record is not None
        assert stale_origin is not None
        assert stale_origin.route == "/informacion"

        repaired_item, bridge_changed = sync_data_request_bridge(
            session,
            request_record,
            organization_id=organization_id,
            actor_email=actor_email,
        )
        session.flush()

        assert repaired_item.source_route == expected_route
        assert stale_origin.route == expected_route
        assert bridge_changed is True
        session.rollback()
