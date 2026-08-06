from __future__ import annotations

"""Runtime stabilization for the transversal workflow.

This compatibility layer is deliberately isolated so it can be removed once the
specialized modules expose the complete canonical state model. It prevents
coarse source states from moving WorkItem backwards and avoids notifying the
actor about their own transition.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import workflow_bridge as bridge
from . import workflow_integrations as integrations
from .database import AppUser, OrganizationMembership, WorkItem, WorkItemEvent
from .notifications import create_notification
from .workflow_service import DATA_REQUEST_STATUS_MAP

STATUS_PROGRESS = {
    "draft": 0,
    "assigned": 10,
    "accepted_by_assignee": 20,
    "in_progress": 30,
    "submitted": 40,
    "validating": 50,
    "under_review": 60,
    "accepted_by_reviewer": 70,
    "closed": 80,
}
EXCEPTION_STATUSES = {"blocked", "returned", "cancelled"}
_INSTALLED = False


def source_status_should_override(current_status: str, source_status: str) -> bool:
    """Return whether a source state may replace the current canonical state."""
    if current_status == source_status:
        return True
    if source_status in EXCEPTION_STATUSES or source_status == "closed":
        return True
    if current_status in {"closed", "cancelled"}:
        return False
    if current_status in {"blocked", "returned"}:
        return source_status in {
            "in_progress",
            "submitted",
            "validating",
            "under_review",
            "accepted_by_reviewer",
            "closed",
        }
    return STATUS_PROGRESS.get(source_status, -1) >= STATUS_PROGRESS.get(current_status, -1)


def _remove_pending_sync_events(session: Session, item_id: int, event_code: str) -> None:
    for pending in list(session.new):
        if (
            isinstance(pending, WorkItemEvent)
            and pending.work_item_id == item_id
            and pending.event_code == event_code
        ):
            session.expunge(pending)


def _stable_upsert(
    original,
    session: Session,
    spec,
    actor_email: str,
) -> tuple[WorkItem, bool]:
    existing = session.scalar(
        select(WorkItem).where(
            WorkItem.organization_id == spec.organization_id,
            WorkItem.source_entity_type == spec.entity_type,
            WorkItem.source_entity_id == spec.entity_id,
        )
    )
    before = integrations._snapshot(existing)
    previous = None
    if existing is not None:
        previous = {
            "status_code": existing.status_code,
            "next_action": existing.next_action,
            "closed_at": existing.closed_at,
            "version": existing.version,
            "updated_at": existing.updated_at,
        }

    item, _ = original(session, spec, actor_email)
    if previous and not source_status_should_override(previous["status_code"], spec.status_code):
        item.status_code = previous["status_code"]
        item.next_action = previous["next_action"]
        item.closed_at = previous["closed_at"]
        item.version = previous["version"]
        item.updated_at = previous["updated_at"]
        _remove_pending_sync_events(session, item.id, "synced_from_source")
    return item, before is None or before != integrations._snapshot(item)


def _stable_report_status(original, value: str) -> str:
    key = integrations._key(value)
    if key in {"publicado", "publicada", "cerrado", "cerrada"}:
        return "closed"
    if key in {"aprobado", "aprobada"}:
        return "accepted_by_reviewer"
    return original(value)


def _stable_data_request_sync(
    original,
    session: Session,
    request_record,
    *,
    organization_id: int,
    actor_email: str,
):
    existing = session.scalar(
        select(WorkItem).where(
            WorkItem.organization_id == organization_id,
            WorkItem.source_entity_type == "DataRequest",
            WorkItem.source_entity_id == request_record.id,
        )
    )
    before = bridge._snapshot(existing)
    previous = None
    if existing is not None:
        previous = {
            "status_code": existing.status_code,
            "next_action": existing.next_action,
            "closed_at": existing.closed_at,
            "version": existing.version,
            "updated_at": existing.updated_at,
        }

    item, _ = original(
        session,
        request_record,
        organization_id=organization_id,
        actor_email=actor_email,
    )
    source_status = DATA_REQUEST_STATUS_MAP.get(request_record.status, "assigned")
    if previous and not source_status_should_override(previous["status_code"], source_status):
        item.status_code = previous["status_code"]
        item.next_action = previous["next_action"]
        item.closed_at = previous["closed_at"]
        item.version = previous["version"]
        item.updated_at = previous["updated_at"]
        _remove_pending_sync_events(session, item.id, "source_status_sync")
    return item, before is None or before != bridge._snapshot(item)


def _notify_roles_except_actor(
    session: Session,
    organization_id: int,
    roles: set[str],
    title: str,
    message: str,
    *,
    actor_user_id: int | None,
    link: str,
    priority: str = "Normal",
) -> None:
    memberships = list(
        session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role.in_(roles),
                OrganizationMembership.active.is_(True),
            )
        )
    )
    user_ids = {membership.user_id for membership in memberships}
    if not user_ids:
        user_ids = set(
            session.scalars(
                select(AppUser.id).where(
                    AppUser.organization_id == organization_id,
                    AppUser.role.in_(roles),
                    AppUser.active.is_(True),
                )
            )
        )
    for user_id in sorted(user_ids):
        if actor_user_id is not None and user_id == actor_user_id:
            continue
        create_notification(
            session,
            organization_id,
            title,
            message,
            user_id=user_id,
            link=link,
            category="Mi trabajo",
            priority=priority,
        )


def _notify_assignee(
    session: Session,
    item: WorkItem,
    *,
    actor_user_id: int | None,
    title: str,
    message: str,
    priority: str = "Normal",
) -> None:
    if item.assignee_user_id:
        if item.assignee_user_id != actor_user_id:
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
        _notify_roles_except_actor(
            session,
            item.organization_id,
            {item.assignee_role},
            title,
            message,
            actor_user_id=actor_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
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
    if item.requester_user_id:
        if item.requester_user_id != actor_user_id:
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
        _notify_roles_except_actor(
            session,
            item.organization_id,
            fallback_roles,
            title,
            message,
            actor_user_id=actor_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
        )


def _notify_transition(
    session: Session,
    item: WorkItem,
    user: dict[str, object],
    previous_status: str,
) -> None:
    label = bridge._status_label(item)
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
        _notify_roles_except_actor(
            session,
            item.organization_id,
            {"Consultor", "Revisor"},
            title,
            message,
            actor_user_id=actor_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
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
        _notify_roles_except_actor(
            session,
            item.organization_id,
            {"Administrador", "Consultor", "Revisor"},
            f"Tarea reabierta: {item.title}",
            "Una tarea previamente cerrada fue reabierta con motivo documentado.",
            actor_user_id=actor_user_id,
            link=f"/mi-trabajo#tarea-{item.id}",
            priority="Alta",
        )


def install_workflow_stabilization() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original_upsert = integrations._upsert
    original_report_status = integrations._report_status
    original_data_request_sync = bridge.sync_data_request

    def stable_upsert(session: Session, spec, actor_email: str):
        return _stable_upsert(original_upsert, session, spec, actor_email)

    def stable_report_status(value: str) -> str:
        return _stable_report_status(original_report_status, value)

    def stable_data_request_sync(
        session: Session,
        request_record,
        *,
        organization_id: int,
        actor_email: str,
    ):
        return _stable_data_request_sync(
            original_data_request_sync,
            session,
            request_record,
            organization_id=organization_id,
            actor_email=actor_email,
        )

    integrations._upsert = stable_upsert
    integrations._report_status = stable_report_status
    integrations.source_status_should_override = source_status_should_override
    bridge.sync_data_request = stable_data_request_sync
    bridge._notify_assignee = _notify_assignee
    bridge._notify_requester = _notify_requester
    bridge._notify_transition = _notify_transition
    _INSTALLED = True
