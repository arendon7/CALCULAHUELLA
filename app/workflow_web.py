from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import product_experience
from .database import Inventory, WorkItem, get_db
from .workflow_domain import CANONICAL_STAGES, STATUSES, WORK_ITEM_TYPES
from .workflow_bridge import sync_data_requests, transition_work_item
from .workflow_service import (
    ACTION_LABELS,
    ACTIONS_REQUIRING_REASON,
    WorkflowServiceError,
    actions_for_item,
    create_work_item,
    status_label,
    visible_work_items,
    work_item_summary,
)


STATUS_CODES = {item.code for item in STATUSES}
STAGE_CODES = {item.code for item in CANONICAL_STAGES}


def _work_navigation_item() -> dict[str, object]:
    return {
        "label": "Mi trabajo",
        "href": "/mi-trabajo",
        "active": "work_items",
        "icon": "✓",
        "any_capability": (),
        "roles": (),
    }


def _install_work_navigation() -> None:
    """Promote Mi trabajo without deleting the existing dashboard or full navigation."""
    for role, sections in tuple(product_experience.ROLE_ESSENTIAL_SECTIONS.items()):
        if not sections:
            continue
        first = dict(sections[0])
        items = list(first.get("items", ()))
        if any(item.get("active") == "work_items" for item in items):
            continue
        remaining = [item for item in items if item.get("active") != "dashboard"]
        first["items"] = (_work_navigation_item(), *remaining)
        product_experience.ROLE_ESSENTIAL_SECTIONS[role] = (first, *sections[1:])

    core_sections = list(product_experience.CORE_SECTIONS)
    if core_sections:
        first = dict(core_sections[0])
        items = list(first.get("items", ()))
        if not any(item.get("active") == "work_items" for item in items):
            first["items"] = (_work_navigation_item(), *items)
            core_sections[0] = first
            product_experience.CORE_SECTIONS = tuple(core_sections)


def _set_flash(request: Request, message: str, level: str = "success") -> None:
    request.session["flash"] = {"message": message, "level": level}


def _parse_optional_date(value: str) -> date | None:
    if not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise WorkflowServiceError("La fecha límite no tiene un formato válido.") from exc


def _filter_items_by_inventory(items: list[WorkItem], inventory_filter: str) -> list[WorkItem]:
    selected = inventory_filter.strip()
    if not selected:
        return items
    if selected == "transversal":
        return [item for item in items if item.inventory_id is None]
    if selected.isdigit():
        selected_id = int(selected)
        return [item for item in items if item.inventory_id == selected_id]
    return []


def _work_queue_url(
    *,
    status: str = "",
    stage: str = "",
    scope: str = "",
    inventory_id: str = "",
    work_item_id: int | None = None,
) -> str:
    params: dict[str, str] = {}
    if status in STATUS_CODES:
        params["status"] = status
    if stage in STAGE_CODES:
        params["stage"] = stage
    if scope in {"mine", "all"}:
        params["scope"] = scope
    selected_inventory = inventory_id.strip()
    if selected_inventory == "transversal" or selected_inventory.isdigit():
        params["inventory_id"] = selected_inventory
    url = "/mi-trabajo"
    if params:
        url = f"{url}?{urlencode(params)}"
    if work_item_id is not None:
        url = f"{url}#tarea-{work_item_id}"
    return url


def register_workflow_routes(app, templates, common_context, require_user) -> None:
    _install_work_navigation()

    @app.get("/mi-trabajo", response_class=HTMLResponse)
    def work_items_page(
        request: Request,
        status: str = "",
        stage: str = "",
        scope: str = "all",
        inventory_id: str = "",
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        sync_result = sync_data_requests(
            session,
            int(user["organization_id"]),
            str(user["email"]),
        )
        if sync_result["changed"]:
            session.commit()

        capabilities = set(user.get("capabilities") or set())
        can_view_all = bool(
            capabilities
            & {
                "manage_workflow",
                "validate_workflow",
                "review_workflow",
                "approve_workflow",
                "audit_workflow",
            }
        )
        selected_scope = "all" if scope == "all" and can_view_all else "mine"
        items = visible_work_items(
            session,
            user,
            status_code=status,
            stage_code=stage,
            scope=selected_scope,
        )
        inventories = list(
            session.scalars(
                select(Inventory)
                .where(Inventory.organization_id == int(user["organization_id"]))
                .order_by(Inventory.start_date.desc(), Inventory.id.desc())
            )
        )
        inventory_by_id = {inventory.id: inventory for inventory in inventories}
        selected_inventory_filter = inventory_id.strip()
        if selected_inventory_filter.isdigit() and int(selected_inventory_filter) not in inventory_by_id:
            selected_inventory_filter = "__invalid__"
        items = _filter_items_by_inventory(items, selected_inventory_filter)
        actions = {item.id: actions_for_item(item, user) for item in items}
        return templates.TemplateResponse(
            request=request,
            name="work_items.html",
            context=common_context(
                request,
                session,
                user,
                "work_items",
                items=items,
                summary=work_item_summary(items),
                actions=actions,
                action_labels=ACTION_LABELS,
                reason_actions=ACTIONS_REQUIRING_REASON,
                status_label=status_label,
                stages=CANONICAL_STAGES,
                statuses=STATUSES,
                work_types=WORK_ITEM_TYPES,
                inventories=inventories,
                inventory_by_id=inventory_by_id,
                selected_status=status,
                selected_stage=stage,
                selected_scope=selected_scope,
                selected_inventory_filter=selected_inventory_filter,
                can_view_all=can_view_all,
                can_create="manage_workflow" in capabilities,
                sync_result=sync_result,
                today=date.today(),
            ),
        )

    @app.post("/mi-trabajo/nueva")
    def work_item_create(
        request: Request,
        title: str = Form(...),
        work_type: str = Form(...),
        description: str = Form(""),
        inventory_id: str = Form(""),
        priority: str = Form("normal"),
        due_date: str = Form(""),
        assignee_email: str = Form(""),
        assignee_role: str = Form(""),
        assignee_area: str = Form(""),
        acceptance_criteria: str = Form(...),
        next_action: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        try:
            item = create_work_item(
                session,
                user,
                title=title,
                work_type=work_type,
                description=description,
                inventory_id=int(inventory_id) if inventory_id.isdigit() else None,
                priority=priority,
                due_date=_parse_optional_date(due_date),
                assignee_email=assignee_email,
                assignee_role=assignee_role,
                assignee_area=assignee_area,
                acceptance_criteria=acceptance_criteria,
                next_action=next_action,
            )
            session.commit()
            _set_flash(request, f"La tarea #{item.id} fue creada y asignada.")
        except WorkflowServiceError as exc:
            session.rollback()
            _set_flash(request, str(exc), "error")
        return RedirectResponse("/mi-trabajo", status_code=303)

    @app.post("/mi-trabajo/sincronizar")
    def work_items_sync(
        request: Request,
        return_status: str = Form(""),
        return_stage: str = Form(""),
        return_scope: str = Form(""),
        return_inventory_id: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if "manage_workflow" not in set(user.get("capabilities") or set()):
            raise HTTPException(403, "Tu rol no puede ejecutar la sincronización manual.")
        result = sync_data_requests(
            session,
            int(user["organization_id"]),
            str(user["email"]),
        )
        session.commit()
        _set_flash(
            request,
            f"Sincronización terminada: {result['total']} solicitudes revisadas y {result['changed']} tareas actualizadas.",
        )
        return RedirectResponse(
            _work_queue_url(
                status=return_status,
                stage=return_stage,
                scope=return_scope,
                inventory_id=return_inventory_id,
            ),
            status_code=303,
        )

    @app.post("/mi-trabajo/{work_item_id}/accion")
    def work_item_action(
        work_item_id: int,
        request: Request,
        action: str = Form(...),
        comment: str = Form(""),
        expected_version: int = Form(...),
        return_status: str = Form(""),
        return_stage: str = Form(""),
        return_scope: str = Form(""),
        return_inventory_id: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        item = session.scalar(
            select(WorkItem)
            .where(
                WorkItem.id == work_item_id,
                WorkItem.organization_id == int(user["organization_id"]),
            )
            .options(selectinload(WorkItem.events), selectinload(WorkItem.links))
        )
        if not item:
            raise HTTPException(404, "Tarea no encontrada.")
        try:
            transition_work_item(
                session,
                item,
                user,
                action=action,
                comment=comment,
                expected_version=expected_version,
            )
            session.commit()
            _set_flash(request, f"La tarea #{item.id} cambió a {status_label(item.status_code)}.")
        except WorkflowServiceError as exc:
            session.rollback()
            _set_flash(request, str(exc), "error")
        return RedirectResponse(
            _work_queue_url(
                status=return_status,
                stage=return_stage,
                scope=return_scope,
                inventory_id=return_inventory_id,
                work_item_id=item.id,
            ),
            status_code=303,
        )

    @app.get("/api/mi-trabajo")
    def work_items_api(
        scope: str = "mine",
        inventory_id: str = "",
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        capabilities = set(user.get("capabilities") or set())
        can_view_all = bool(
            capabilities
            & {
                "manage_workflow",
                "validate_workflow",
                "review_workflow",
                "approve_workflow",
                "audit_workflow",
            }
        )
        selected_scope = "all" if scope == "all" and can_view_all else "mine"
        items = visible_work_items(session, user, scope=selected_scope)
        selected_inventory_filter = inventory_id.strip()
        items = _filter_items_by_inventory(items, selected_inventory_filter)
        return JSONResponse(
            {
                "scope": selected_scope,
                "inventory_filter": selected_inventory_filter,
                "summary": work_item_summary(items),
                "items": [
                    {
                        "id": item.id,
                        "inventory_id": item.inventory_id,
                        "title": item.title,
                        "stage": item.stage_code,
                        "type": item.work_type,
                        "status": item.status_code,
                        "status_label": status_label(item.status_code),
                        "priority": item.priority,
                        "assignee": item.assignee_email or item.assignee_role or item.assignee_area,
                        "due_date": item.due_date.isoformat() if item.due_date else None,
                        "next_action": item.next_action,
                        "source_route": item.source_route,
                        "version": item.version,
                    }
                    for item in items
                ],
            }
        )
