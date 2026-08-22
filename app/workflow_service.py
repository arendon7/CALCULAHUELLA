from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .database import (
    AppUser,
    DataRequest,
    Inventory,
    OrganizationMembership,
    WorkItem,
    WorkItemEvent,
    WorkItemLink,
    add_audit,
)
from .workflow_domain import (
    DEFAULT_STAGE_BY_WORK_TYPE,
    PRIORITIES,
    STATUS_BY_CODE,
    WORK_ITEM_TYPES,
    WorkflowRuleError,
    allowed_actions,
    validate_transition,
)


MANAGEMENT_CAPABILITIES = {
    "manage_workflow",
    "validate_workflow",
    "review_workflow",
    "approve_workflow",
    "audit_workflow",
}

DATA_REQUEST_STATUS_MAP = {
    "Pendiente": "assigned",
    "En preparación": "in_progress",
    "Cargado": "submitted",
    "En revisión": "under_review",
    "Completado": "closed",
    "Devuelto": "returned",
}

ACTION_LABELS = {
    "assign": "Asignar responsable",
    "accept_assignment": "Aceptar asignación",
    "start": "Iniciar preparación",
    "block": "Registrar bloqueo",
    "resume": "Reanudar trabajo",
    "submit": "Entregar para validación",
    "start_validation": "Iniciar validación",
    "send_to_review": "Enviar a revisión",
    "accept_delivery": "Aceptar entrega",
    "return_for_correction": "Devolver para corrección",
    "restart_correction": "Iniciar corrección",
    "close": "Cerrar tarea",
    "reopen": "Reabrir con motivo",
    "cancel": "Cancelar con motivo",
}

ACTIONS_REQUIRING_REASON = {"block", "return_for_correction", "reopen", "cancel"}


class WorkflowServiceError(ValueError):
    """Raised when a workflow service operation cannot be completed safely."""


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _event(
    item: WorkItem,
    *,
    event_code: str,
    actor_email: str,
    actor_role: str,
    from_status: str = "",
    to_status: str = "",
    comment: str = "",
) -> WorkItemEvent:
    return WorkItemEvent(
        work_item=item,
        event_code=event_code,
        from_status_code=from_status,
        to_status_code=to_status,
        actor_email=actor_email,
        actor_role=actor_role,
        comment=comment.strip(),
    )


def _assignee_from_email(session: Session, organization_id: int, email: str) -> tuple[int | None, str]:
    normalized = _normalize_email(email)
    if not normalized:
        return None, ""
    membership = session.scalar(
        select(OrganizationMembership)
        .join(AppUser, AppUser.id == OrganizationMembership.user_id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.active.is_(True),
            func.lower(AppUser.email) == normalized,
        )
    )
    if not membership:
        return None, ""
    return membership.user_id, membership.role


def create_work_item(
    session: Session,
    user: dict[str, object],
    *,
    title: str,
    work_type: str,
    description: str = "",
    inventory_id: int | None = None,
    priority: str = "normal",
    due_date: date | None = None,
    assignee_email: str = "",
    assignee_role: str = "",
    assignee_area: str = "",
    acceptance_criteria: str = "",
    next_action: str = "",
    source_entity_type: str = "",
    source_entity_id: int | None = None,
    source_route: str = "",
) -> WorkItem:
    capabilities = set(user.get("capabilities") or set())
    if "manage_workflow" not in capabilities:
        raise WorkflowServiceError("El rol activo no puede crear ni asignar trabajo.")
    normalized_title = title.strip()
    if not normalized_title:
        raise WorkflowServiceError("La tarea requiere un título claro.")
    if work_type not in WORK_ITEM_TYPES:
        raise WorkflowServiceError("Tipo de trabajo inválido.")
    if priority not in PRIORITIES:
        raise WorkflowServiceError("Prioridad inválida.")
    normalized_email = _normalize_email(assignee_email)
    if not (normalized_email or assignee_role.strip() or assignee_area.strip()):
        raise WorkflowServiceError("La tarea requiere una persona, rol o área responsable.")
    if not acceptance_criteria.strip():
        raise WorkflowServiceError("La tarea requiere criterios de aceptación verificables.")

    organization_id = int(user["organization_id"])
    if inventory_id is not None:
        valid_inventory = session.scalar(
            select(Inventory.id).where(
                Inventory.id == inventory_id,
                Inventory.organization_id == organization_id,
            )
        )
        if not valid_inventory:
            raise WorkflowServiceError("El inventario seleccionado no pertenece a la organización activa.")

    assignee_user_id, membership_role = _assignee_from_email(session, organization_id, normalized_email)
    final_role = assignee_role.strip() or membership_role
    item = WorkItem(
        organization_id=organization_id,
        inventory_id=inventory_id,
        stage_code=DEFAULT_STAGE_BY_WORK_TYPE[work_type],
        work_type=work_type,
        title=normalized_title,
        description=description.strip(),
        status_code="assigned",
        priority=priority,
        requester_user_id=int(user["id"]),
        requester_email=str(user["email"]),
        assignee_user_id=assignee_user_id,
        assignee_email=normalized_email,
        assignee_role=final_role,
        assignee_area=assignee_area.strip(),
        due_date=due_date,
        acceptance_criteria=acceptance_criteria.strip(),
        next_action=next_action.strip() or "Aceptar la asignación y comenzar la preparación.",
        source_entity_type=source_entity_type.strip(),
        source_entity_id=source_entity_id,
        source_route=source_route.strip(),
        created_by=str(user["email"]),
    )
    session.add(item)
    session.flush()
    session.add(
        _event(
            item,
            event_code="created_and_assigned",
            actor_email=str(user["email"]),
            actor_role=str(user["role"]),
            from_status="draft",
            to_status="assigned",
            comment="Tarea creada con responsable y criterio de aceptación.",
        )
    )
    add_audit(
        session,
        organization_id,
        str(user["email"]),
        "ASIGNAR",
        "Trabajo",
        item.title,
        detail=f"Tipo {work_type}; responsable {normalized_email or final_role or assignee_area}",
    )
    return item


def _can_execute_item(item: WorkItem, user: dict[str, object], action: str) -> bool:
    capabilities = set(user.get("capabilities") or set())
    if "manage_workflow" in capabilities or action not in {
        "accept_assignment",
        "start",
        "block",
        "resume",
        "submit",
        "restart_correction",
    }:
        return True
    user_id = int(user["id"])
    email = _normalize_email(str(user["email"]))
    role = str(user["role"])
    return bool(
        (item.assignee_user_id and item.assignee_user_id == user_id)
        or (item.assignee_email and _normalize_email(item.assignee_email) == email)
        or (item.assignee_role and item.assignee_role == role)
    )


def transition_work_item(
    session: Session,
    item: WorkItem,
    user: dict[str, object],
    *,
    action: str,
    comment: str = "",
    expected_version: int | None = None,
) -> WorkItem:
    if item.organization_id != int(user["organization_id"]):
        raise WorkflowServiceError("La tarea no pertenece a la organización activa.")
    if expected_version is not None and item.version != expected_version:
        raise WorkflowServiceError("La tarea cambió mientras estaba abierta. Actualiza la página antes de continuar.")
    if not _can_execute_item(item, user, action):
        raise WorkflowServiceError("Solo el responsable asignado puede ejecutar esta acción.")

    reason = comment.strip() if action in ACTIONS_REQUIRING_REASON else ""
    try:
        target = validate_transition(
            item.status_code,
            action,
            user.get("capabilities") or set(),
            reason=reason,
            assignee_present=bool(item.assignee_user_id or item.assignee_email or item.assignee_role or item.assignee_area),
            acceptance_criteria_present=bool(item.acceptance_criteria.strip()),
        )
    except WorkflowRuleError as exc:
        raise WorkflowServiceError(str(exc)) from exc
    previous = item.status_code
    now = datetime.now(UTC)
    item.status_code = target
    item.version += 1
    item.updated_at = now

    if action == "accept_assignment":
        item.accepted_at = now
        item.next_action = "Preparar la entrega conforme al criterio de aceptación."
    elif action in {"start", "resume", "restart_correction"}:
        item.blocking_reason = ""
        item.next_action = "Completar la preparación y entregar para validación."
    elif action == "block":
        item.blocking_reason = comment.strip()
        item.next_action = "Resolver el bloqueo documentado antes de reanudar."
    elif action == "submit":
        item.submitted_at = now
        item.next_action = "La entrega espera validación."
    elif action == "start_validation":
        item.next_action = "Validar integridad, formato y criterios de aceptación."
    elif action == "send_to_review":
        item.next_action = "La entrega espera revisión técnica."
    elif action == "accept_delivery":
        item.reviewed_at = now
        item.next_action = "Cerrar la tarea y actualizar la puerta correspondiente."
    elif action == "return_for_correction":
        item.reviewed_at = now
        item.next_action = "Corregir los puntos indicados y entregar nuevamente."
    elif action == "close":
        item.approved_at = now
        item.closed_at = now
        item.next_action = "Tarea cerrada."
    elif action == "reopen":
        item.closed_at = None
        item.next_action = "Atender el motivo de reapertura y entregar una nueva corrección."
    elif action == "cancel":
        item.closed_at = now
        item.next_action = "Tarea cancelada con motivo documentado."

    session.add(
        _event(
            item,
            event_code=action,
            actor_email=str(user["email"]),
            actor_role=str(user["role"]),
            from_status=previous,
            to_status=target,
            comment=comment,
        )
    )
    add_audit(
        session,
        item.organization_id,
        str(user["email"]),
        action.upper(),
        "Trabajo",
        item.title,
        detail=f"{previous} -> {target}",
        reason=comment.strip() if action in ACTIONS_REQUIRING_REASON else "",
    )
    return item


def _mapped_request_status(value: str) -> str:
    return DATA_REQUEST_STATUS_MAP.get(value, "assigned")


def _next_action_for_status(status_code: str) -> str:
    return {
        "assigned": "Aceptar la asignación y comenzar la preparación.",
        "in_progress": "Completar la preparación y entregar para validación.",
        "submitted": "La entrega espera validación.",
        "validating": "Validar integridad, formato y criterios de aceptación.",
        "under_review": "La entrega espera revisión técnica.",
        "accepted_by_reviewer": "Cerrar la tarea y actualizar la puerta correspondiente.",
        "returned": "Corregir los puntos indicados y entregar nuevamente.",
        "closed": "Tarea cerrada.",
        "cancelled": "Tarea cancelada con motivo documentado.",
    }.get(status_code, "Revisar el estado y definir la acción siguiente.")


def sync_data_request(
    session: Session,
    request_record: DataRequest,
    *,
    organization_id: int,
    actor_email: str,
) -> tuple[WorkItem, bool]:
    existing = session.scalar(
        select(WorkItem).where(
            WorkItem.organization_id == organization_id,
            WorkItem.source_entity_type == "DataRequest",
            WorkItem.source_entity_id == request_record.id,
        )
    )
    normalized_target = _normalize_email(request_record.requested_to)
    is_email = "@" in normalized_target
    assignee_user_id, membership_role = _assignee_from_email(
        session,
        organization_id,
        normalized_target if is_email else "",
    )
    mapped_status = _mapped_request_status(request_record.status)
    acceptance = request_record.instructions.strip() or (
        "Entregar el dato solicitado con periodo, unidad, origen y evidencia suficiente."
    )
    period_route = f"/inventarios/{request_record.inventory_id}"
    changed = False

    if not existing:
        item = WorkItem(
            organization_id=organization_id,
            inventory_id=request_record.inventory_id,
            stage_code="collect",
            work_type="data_request",
            title=request_record.title.strip(),
            description=request_record.instructions.strip(),
            status_code=mapped_status,
            priority="normal",
            requester_email=actor_email,
            assignee_user_id=assignee_user_id,
            assignee_email=normalized_target if is_email else "",
            assignee_role=membership_role,
            assignee_area="" if is_email else request_record.requested_to.strip(),
            due_date=request_record.due_date,
            acceptance_criteria=acceptance,
            next_action=_next_action_for_status(mapped_status),
            source_entity_type="DataRequest",
            source_entity_id=request_record.id,
            source_route=period_route,
            created_by=actor_email,
            closed_at=(request_record.completed_at or datetime.now(UTC)) if mapped_status == "closed" else None,
        )
        session.add(item)
        session.flush()
        session.add(
            WorkItemLink(
                work_item_id=item.id,
                entity_type="DataRequest",
                entity_id=request_record.id,
                relationship_type="origin",
                label=request_record.title.strip(),
                route=period_route,
            )
        )
        add_audit(
            session,
            organization_id,
            actor_email,
            "SINCRONIZAR",
            "Trabajo",
            item.title,
            detail=f"Solicitud de información #{request_record.id}",
        )
        session.add(
            _event(
                item,
                event_code="synced_from_data_request",
                actor_email=actor_email,
                actor_role="Sistema",
                from_status="",
                to_status=mapped_status,
                comment=f"Solicitud #{request_record.id} incorporada a Mi trabajo.",
            )
        )
        return item, True

    item = existing
    new_values = {
        "inventory_id": request_record.inventory_id,
        "title": request_record.title.strip(),
        "description": request_record.instructions.strip(),
        "due_date": request_record.due_date,
        "acceptance_criteria": acceptance,
        "assignee_user_id": assignee_user_id,
        "assignee_email": normalized_target if is_email else "",
        "assignee_role": membership_role,
        "assignee_area": "" if is_email else request_record.requested_to.strip(),
        "source_route": period_route,
    }
    for field, value in new_values.items():
        if getattr(item, field) != value:
            setattr(item, field, value)
            changed = True

    origin_link = session.scalar(
        select(WorkItemLink).where(
            WorkItemLink.work_item_id == item.id,
            WorkItemLink.entity_type == "DataRequest",
            WorkItemLink.entity_id == request_record.id,
            WorkItemLink.relationship_type == "origin",
        )
    )
    if origin_link is None:
        session.add(
            WorkItemLink(
                work_item_id=item.id,
                entity_type="DataRequest",
                entity_id=request_record.id,
                relationship_type="origin",
                label=request_record.title.strip(),
                route=period_route,
            )
        )
        changed = True
    else:
        if origin_link.route != period_route:
            origin_link.route = period_route
            changed = True
        if origin_link.label != request_record.title.strip():
            origin_link.label = request_record.title.strip()
            changed = True

    if item.status_code != mapped_status:
        previous = item.status_code
        item.status_code = mapped_status
        item.next_action = _next_action_for_status(mapped_status)
        item.closed_at = (request_record.completed_at or datetime.now(UTC)) if mapped_status == "closed" else None
        item.version += 1
        item.updated_at = datetime.now(UTC)
        session.add(
            _event(
                item,
                event_code="source_status_sync",
                actor_email=actor_email,
                actor_role="Sistema",
                from_status=previous,
                to_status=mapped_status,
                comment=f"Estado sincronizado desde solicitud: {request_record.status}.",
            )
        )
        changed = True
    return item, changed


def sync_data_requests(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    requests = list(
        session.scalars(
            select(DataRequest)
            .join(Inventory, Inventory.id == DataRequest.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(DataRequest.id)
        )
    )
    created_or_updated = 0
    for record in requests:
        _, changed = sync_data_request(
            session,
            record,
            organization_id=organization_id,
            actor_email=actor_email,
        )
        created_or_updated += int(changed)
    return {"total": len(requests), "changed": created_or_updated}


def visible_work_items(
    session: Session,
    user: dict[str, object],
    *,
    status_code: str = "",
    stage_code: str = "",
    scope: str = "mine",
) -> list[WorkItem]:
    organization_id = int(user["organization_id"])
    query = select(WorkItem).where(WorkItem.organization_id == organization_id)
    capabilities = set(user.get("capabilities") or set())
    privileged = bool(capabilities & MANAGEMENT_CAPABILITIES)
    user_filter = or_(
        WorkItem.assignee_user_id == int(user["id"]),
        func.lower(WorkItem.assignee_email) == _normalize_email(str(user["email"])),
        WorkItem.assignee_role == str(user["role"]),
        WorkItem.requester_user_id == int(user["id"]),
        func.lower(WorkItem.requester_email) == _normalize_email(str(user["email"])),
    )
    if not privileged or scope != "all":
        query = query.where(user_filter)
    if status_code:
        query = query.where(WorkItem.status_code == status_code)
    if stage_code:
        query = query.where(WorkItem.stage_code == stage_code)
    return list(
        session.scalars(
            query.options(selectinload(WorkItem.events), selectinload(WorkItem.links)).order_by(
                WorkItem.closed_at.is_not(None),
                WorkItem.due_date.is_(None),
                WorkItem.due_date,
                WorkItem.updated_at.desc(),
                WorkItem.id.desc(),
            )
        )
    )


def work_item_summary(items: list[WorkItem], *, today: date | None = None) -> dict[str, int]:
    current = today or date.today()
    open_items = [item for item in items if item.status_code not in {"closed", "cancelled"}]
    return {
        "total": len(items),
        "open": len(open_items),
        "overdue": sum(1 for item in open_items if item.due_date and item.due_date < current),
        "returned": sum(1 for item in open_items if item.status_code == "returned"),
        "blocked": sum(1 for item in open_items if item.status_code == "blocked"),
        "under_review": sum(1 for item in open_items if item.status_code in {"validating", "under_review", "accepted_by_reviewer"}),
    }


def actions_for_item(item: WorkItem, user: dict[str, object]) -> tuple[str, ...]:
    actions = allowed_actions(item.status_code, user.get("capabilities") or set())
    return tuple(action for action in actions if _can_execute_item(item, user, action))


def status_label(status_code: str) -> str:
    definition = STATUS_BY_CODE.get(status_code)
    return definition.label if definition else status_code
