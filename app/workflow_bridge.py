from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import DataRequest, Inventory, WorkItem
from .workflow_service import (
    sync_data_request as _base_sync_data_request,
    transition_work_item as _base_transition_work_item,
)


WORK_ITEM_TO_DATA_REQUEST_STATUS = {
    "assigned": "Pendiente",
    "accepted_by_assignee": "En preparación",
    "in_progress": "En preparación",
    "blocked": "En preparación",
    "submitted": "Cargado",
    "validating": "En revisión",
    "under_review": "En revisión",
    "accepted_by_reviewer": "En revisión",
    "returned": "Devuelto",
    "closed": "Completado",
}


def _snapshot(item: WorkItem | None) -> tuple[object, ...] | None:
    if item is None:
        return None
    return (
        item.inventory_id,
        item.title,
        item.description,
        item.status_code,
        item.assignee_user_id,
        item.assignee_email,
        item.assignee_role,
        item.assignee_area,
        item.requester_user_id,
        item.requester_email,
        item.due_date,
        item.acceptance_criteria,
        item.next_action,
        item.source_route,
        item.closed_at,
        item.version,
    )


def _sync_request_from_work_item(session: Session, item: WorkItem) -> None:
    if item.source_entity_type != "DataRequest" or not item.source_entity_id:
        return
    request_record = session.get(DataRequest, item.source_entity_id)
    if not request_record or request_record.inventory_id != item.inventory_id:
        return
    mapped_status = WORK_ITEM_TO_DATA_REQUEST_STATUS.get(item.status_code)
    if not mapped_status:
        return
    request_record.status = mapped_status
    request_record.completed_at = item.closed_at if mapped_status == "Completado" else None


def transition_work_item(session: Session, item: WorkItem, user: dict[str, object], **kwargs) -> WorkItem:
    """Apply the canonical transition and mirror it to the legacy request when present."""
    result = _base_transition_work_item(session, item, user, **kwargs)
    _sync_request_from_work_item(session, result)
    return result


def sync_data_request(
    session: Session,
    request_record: DataRequest,
    *,
    organization_id: int,
    actor_email: str,
) -> tuple[WorkItem, bool]:
    """Import a legacy request without leaking visibility through the importing user."""
    existing = session.scalar(
        select(WorkItem).where(
            WorkItem.organization_id == organization_id,
            WorkItem.source_entity_type == "DataRequest",
            WorkItem.source_entity_id == request_record.id,
        )
    )
    before = _snapshot(existing)
    item, _ = _base_sync_data_request(
        session,
        request_record,
        organization_id=organization_id,
        actor_email=actor_email,
    )
    is_email_assignment = "@" in request_record.requested_to.strip()
    if item.requester_email or item.requester_user_id:
        item.requester_email = ""
        item.requester_user_id = None
    if not is_email_assignment and not item.assignee_role:
        item.assignee_role = "Cliente"
    if item.status_code == "closed" and item.closed_at is None:
        item.closed_at = request_record.completed_at or datetime.now(UTC)
    return item, before is None or before != _snapshot(item)


def sync_data_requests(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    requests = list(
        session.scalars(
            select(DataRequest)
            .join(Inventory, Inventory.id == DataRequest.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(DataRequest.id)
        )
    )
    changed = 0
    for request_record in requests:
        _, item_changed = sync_data_request(
            session,
            request_record,
            organization_id=organization_id,
            actor_email=actor_email,
        )
        changed += int(item_changed)
    return {"total": len(requests), "changed": changed}
