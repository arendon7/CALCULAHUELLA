from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import workflow_service as _workflow_service
from .database import DataRequest, Inventory, WorkItem
from .notifications import create_notification, notify_roles
from .workflow_domain import STATUS_BY_CODE
from .workflow_integrations import mirror_source_from_work_item, sync_specialized_work_items
from .workflow_service import (
    create_work_item as _base_create_work_item,
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


def _status_label(item: WorkItem) -> str:
    definition = STATUS_BY_CODE.get(item.status_code)
    return definition.label if definition else item.status_code


def _notify_assignee(
    session: Session,
    item: WorkItem,
    *,
    actor_user_id: int | None,
    title: str,
    message: str,
    priority: str = "Normal",
) -> None:
    if item.assignee_user_id and item.assignee_user_id != actor_user_id:
        create_notification(
            session,
            item.organization_id,
            title,
            message,
            user_id=item.assignee_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority=priority,
        )
        return
    if item.assignee_role:
        notify_roles(
            session,
            item.organization_id,
            {item.assignee_role},
            title,
            message,
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority=priority,
        )


def _notify_requester(
    session: Session,
    item: WorkItem,
    *,
    actor_user_id: int | None,
    title: str,
    message: str,
    fallback_roles: set[str] | None = None,
) -> None:
    if item.requester_user_id and item.requester_user_id != actor_user_id:
        create_notification(
            session,
            item.organization_id,
            title,
            message,
            user_id=item.requester_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority="Normal",
        )
        return
    if fallback_roles:
        notify_roles(
            session,
            item.organization_id,
            fallback_roles,
            title,
            message,
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority="Normal",
        )


def create_work_item(session: Session, user: dict[str, object], **kwargs) -> WorkItem:
    """Ensure an area-only assignment has a visible owner and notify it."""
    area = str(kwargs.get("assignee_area") or "").strip()
    email = str(kwargs.get("assignee_email") or "").strip()
    role = str(kwargs.get("assignee_role") or "").strip()
    if area and not email and not role:
        kwargs["assignee_role"] = "Cliente"
    item = _base_create_work_item(session, user, **kwargs)
    _notify_assignee(
        session,
        item,
        actor_user_id=int(user["id"]),
        title=f"Nueva tarea: {item.title}",
        message=f"Se te asignó una tarea. Próxima acción: {item.next_action}",
        priority="Alta" if item.priority in {"high", "critical"} else "Normal",
    )
    return item


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


def _notify_transition(
    session: Session,
    item: WorkItem,
    user: dict[str, object],
    previous_status: str,
) -> None:
    label = _status_label(item)
    title = f"Tarea #{item.id}: {label}"
    message = f"{item.title}. Próxima acción: {item.next_action}"
    actor_user_id = int(user["id"])

    if item.status_code in {"assigned", "accepted_by_assignee", "in_progress", "blocked", "returned"}:
        _notify_assignee(
            session,
            item,
            actor_user_id=actor_user_id,
            title=title,
            message=message,
            priority="Alta" if item.status_code in {"blocked", "returned"} else "Normal",
        )
    elif item.status_code in {"submitted", "validating", "under_review"}:
        notify_roles(
            session,
            item.organization_id,
            {"Consultor", "Revisor"},
            title,
            message,
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority="Alta" if item.priority in {"high", "critical"} else "Normal",
        )
    elif item.status_code in {"accepted_by_reviewer", "closed", "cancelled"}:
        _notify_requester(
            session,
            item,
            actor_user_id=actor_user_id,
            title=title,
            message=message,
            fallback_roles={"Administrador", "Consultor"},
        )

    if previous_status == "closed" and item.status_code == "returned":
        notify_roles(
            session,
            item.organization_id,
            {"Administrador", "Consultor", "Revisor"},
            f"Tarea reabierta: {item.title}",
            "Una tarea previamente cerrada fue reabierta con motivo documentado.",
            link=f"/mi-trabajo#tarea-{item.id}",
            category="Mi trabajo",
            priority="Alta",
        )


def transition_work_item(session: Session, item: WorkItem, user: dict[str, object], **kwargs) -> WorkItem:
    """Apply a canonical transition, mirror its source and notify the next actor."""
    previous_status = item.status_code
    comment = str(kwargs.get("comment") or "")
    result = _base_transition_work_item(session, item, user, **kwargs)
    _sync_request_from_work_item(session, result)
    mirror_source_from_work_item(
        session,
        result,
        actor_email=str(user["email"]),
        actor_role=str(user["role"]),
        comment=comment,
    )
    _notify_transition(session, result, user, previous_status)
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


def _sync_data_requests_only(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
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


def sync_data_requests(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    """Synchronize every supported work source while preserving the legacy return contract."""
    requests = _sync_data_requests_only(session, organization_id, actor_email)
    specialized = sync_specialized_work_items(session, organization_id, actor_email)
    return {
        "total": requests["total"],
        "changed": requests["changed"] + int(specialized["changed"]),
    }


# experience_web imports workflow_bridge before workflow_service. Replacing this
# reference keeps the generic service independent while applying compatibility
# defaults and notifications to tasks created from the current web form.
_workflow_service.create_work_item = create_work_item
