from __future__ import annotations

from datetime import date

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import product_experience
from .database import Inventory, WorkItem, get_db
from .delivery_readiness import professional_delivery_summary
from .workflow_domain import CANONICAL_STAGES, STATUSES, WORK_ITEM_TYPES
from .workflow_service import (
    ACTION_LABELS,
    ACTIONS_REQUIRING_REASON,
    WorkflowServiceError,
    actions_for_item,
    create_work_item,
    status_label,
    sync_data_requests,
    transition_work_item,
    visible_work_items,
    work_item_summary,
)


GUIDE_STAGES = (
    {
        "number": "01",
        "name": "Diagnosticar",
        "question": "¿Qué necesita medir la organización y para qué?",
        "output": "Perfil sectorial, propósito, complejidad, datos disponibles y ruta de implementación.",
        "href": "/inteligencia-producto",
    },
    {
        "number": "02",
        "name": "Configurar",
        "question": "¿Qué límites, sedes, fuentes, responsables y criterios regirán el inventario?",
        "output": "Periodo, consolidación, alcances, materialidad, GWP, responsables y criterios documentados.",
        "href": "/metodologia/cierre",
    },
    {
        "number": "03",
        "name": "Recopilar",
        "question": "¿Qué datos y evidencias debe entregar cada responsable?",
        "output": "Solicitudes asignadas, datos de actividad, unidades, periodos y soportes relacionados.",
        "href": "/mi-trabajo",
    },
    {
        "number": "04",
        "name": "Validar y cerrar periodos",
        "question": "¿La información está completa, consistente y lista para congelarse?",
        "output": "Errores resueltos, hallazgos atendidos y periodos cerrados con trazabilidad.",
        "href": "/cierre-mensual",
    },
    {
        "number": "05",
        "name": "Calcular",
        "question": "¿Qué factor representa cada dato y cómo se reproduce el resultado?",
        "output": "Factores aprobados, conversiones, fórmulas, gases, GWP y resultados explicables.",
        "href": "/calculos",
    },
    {
        "number": "06",
        "name": "Revisar y aprobar",
        "question": "¿El resultado cumple los criterios técnicos y de control interno?",
        "output": "Observaciones resueltas, segregación de funciones, decisión y aprobación documentadas.",
        "href": "/control",
    },
    {
        "number": "07",
        "name": "Reportar y controlar publicación",
        "question": "¿Qué versión puede utilizarse, quién la aprobó y para qué destinatario?",
        "output": "Informe versionado, nivel de publicación y expediente de entrega controlado.",
        "href": "/entrega-profesional",
    },
    {
        "number": "08",
        "name": "Reducir y continuar",
        "question": "¿Qué debe cambiar y cómo se prepara el siguiente periodo?",
        "output": "Metas, medidas, responsables, seguimiento y continuidad del nuevo ciclo.",
        "href": "/reduccion",
    },
)

GLOSSARY = (
    ("Dato de actividad", "Magnitud observada que describe una actividad: kWh, litros, kilogramos, kilómetros u otra unidad verificable."),
    ("Factor de emisión", "Coeficiente que relaciona un dato de actividad con una emisión. Debe ser compatible, representativo y documentado."),
    ("Alcance 1", "Emisiones directas de fuentes que controla la organización."),
    ("Alcance 2", "Emisiones asociadas con electricidad, calor, vapor o refrigeración adquiridos."),
    ("Alcance 3", "Otras emisiones indirectas de la cadena de valor, priorizadas según relevancia y propósito."),
    ("CO₂e", "Unidad común que expresa distintos gases de efecto invernadero mediante su potencial de calentamiento global."),
    ("GWP", "Potencial de calentamiento global utilizado para convertir cada gas a CO₂ equivalente."),
    ("Evidencia", "Documento o registro que respalda origen, valor, unidad, periodo y responsable del dato."),
    ("Incertidumbre", "Rango o nivel de confianza asociado con datos, factores, supuestos y resultados."),
    ("Materialidad", "Criterio para priorizar fuentes relevantes por magnitud, riesgo, interés de usuarios o capacidad de gestión."),
    ("Emisión evitada", "Comparación contra un escenario de referencia. No debe descontarse automáticamente del inventario corporativo."),
    ("Compensación", "Instrumento separado del inventario y de la reducción interna; requiere reglas y evidencia propias."),
)


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
    """Promote Mi trabajo while preserving the dashboard route as a secondary view."""
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
            remaining = [item for item in items if item.get("active") != "dashboard"]
            first["items"] = (_work_navigation_item(), *remaining)
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


def register_experience_routes(app, templates, common_context, require_user, get_inventory) -> None:
    _install_work_navigation()

    @app.get("/guia", response_class=HTMLResponse)
    def experience_guide(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user)
        delivery = professional_delivery_summary(session, inventory)
        return templates.TemplateResponse(
            request=request,
            name="guide.html",
            context=common_context(
                request,
                session,
                user,
                "guide",
                inventory=inventory,
                delivery=delivery,
                stages=GUIDE_STAGES,
                glossary=GLOSSARY,
            ),
        )

    @app.get("/mi-trabajo", response_class=HTMLResponse)
    def work_items_page(
        request: Request,
        status: str = "",
        stage: str = "",
        scope: str = "mine",
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
                selected_status=status,
                selected_stage=stage,
                selected_scope=selected_scope,
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
        return RedirectResponse("/mi-trabajo?scope=all", status_code=303)

    @app.post("/mi-trabajo/{work_item_id}/accion")
    def work_item_action(
        work_item_id: int,
        request: Request,
        action: str = Form(...),
        comment: str = Form(""),
        expected_version: int = Form(...),
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
        return RedirectResponse("/mi-trabajo", status_code=303)

    @app.get("/api/mi-trabajo")
    def work_items_api(
        scope: str = "mine",
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
        return JSONResponse(
            {
                "scope": selected_scope,
                "summary": work_item_summary(items),
                "items": [
                    {
                        "id": item.id,
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
