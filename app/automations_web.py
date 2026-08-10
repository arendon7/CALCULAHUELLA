from __future__ import annotations

import json

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .automations import (
    AUTOMATION_TYPES, CADENCES, ROLE_OPTIONS, calculate_next_run, execute_automation, process_due_automations,
)
from .config import settings
from .database import add_audit, get_db
from .db.models import AutomationRun, Inventory, ScheduledAutomation


def register_automation_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory
) -> None:
    @app.get("/automatizaciones", response_class=HTMLResponse)
    def automations_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_automations")
        automations = list(session.scalars(
            select(ScheduledAutomation)
            .where(ScheduledAutomation.organization_id == int(user["organization_id"]))
            .options(selectinload(ScheduledAutomation.inventory), selectinload(ScheduledAutomation.runs))
            .order_by(ScheduledAutomation.active.desc(), ScheduledAutomation.name)
        ))
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
        recent_runs = list(session.scalars(
            select(AutomationRun)
            .join(ScheduledAutomation)
            .where(ScheduledAutomation.organization_id == int(user["organization_id"]))
            .options(selectinload(AutomationRun.automation))
            .order_by(AutomationRun.started_at.desc()).limit(30)
        ))
        return templates.TemplateResponse(
            request=request,
            name="automations.html",
            context=common_context(
                request, session, user, "automations", automations=automations, inventories=inventories,
                recent_runs=recent_runs, automation_types=AUTOMATION_TYPES, cadences=CADENCES,
                role_options=ROLE_OPTIONS, scheduler_enabled=settings.scheduler_enabled,
            ),
        )

    @app.post("/automatizaciones/nueva")
    def automation_create(
        request: Request,
        name: str = Form(...),
        automation_type: str = Form(...),
        cadence: str = Form("Semanal"),
        schedule_time: str = Form("08:00"),
        inventory_id: int | None = Form(None),
        weekday: int | None = Form(None),
        month_day: int | None = Form(None),
        days_before: int = Form(3),
        recipient_roles: list[str] = Form(default=[]),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_automations")
        if automation_type not in AUTOMATION_TYPES or cadence not in CADENCES:
            raise HTTPException(400, "Tipo o frecuencia inválida")
        if inventory_id:
            get_inventory(session, user, inventory_id)
        automation = ScheduledAutomation(
            organization_id=int(user["organization_id"]), inventory_id=inventory_id or None,
            name=name.strip(), automation_type=automation_type, cadence=cadence,
            schedule_time=schedule_time, weekday=weekday, month_day=month_day,
            timezone="America/Bogota", recipient_roles=json.dumps(recipient_roles or ["Administrador", "Consultor"]),
            days_before=max(0, min(days_before, 60)), active=True, created_by=str(user["email"]),
        )
        session.add(automation)
        session.flush()
        automation.next_run_at = calculate_next_run(automation)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Automatización", automation.name, automation.automation_type)
        session.commit()
        set_flash(request, "Automatización creada y programada.")
        return RedirectResponse("/automatizaciones", status_code=303)

    @app.post("/automatizaciones/{automation_id}/estado")
    def automation_toggle(automation_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_automations")
        automation = session.scalar(select(ScheduledAutomation).where(
            ScheduledAutomation.id == automation_id,
            ScheduledAutomation.organization_id == int(user["organization_id"]),
        ))
        if not automation:
            raise HTTPException(404, "Automatización no encontrada")
        automation.active = not automation.active
        automation.next_run_at = calculate_next_run(automation) if automation.active else None
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTIVAR" if automation.active else "DESACTIVAR", "Automatización", automation.name)
        session.commit()
        set_flash(request, f"Automatización {'activada' if automation.active else 'desactivada'}.")
        return RedirectResponse("/automatizaciones", status_code=303)

    @app.post("/automatizaciones/{automation_id}/ejecutar")
    def automation_run_now(automation_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_automations")
        automation = session.scalar(select(ScheduledAutomation).where(
            ScheduledAutomation.id == automation_id,
            ScheduledAutomation.organization_id == int(user["organization_id"]),
        ))
        if not automation:
            raise HTTPException(404, "Automatización no encontrada")
        run = execute_automation(session, automation, triggered_by=str(user["email"]))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EJECUTAR", "Automatización", automation.name, run.summary)
        session.commit()
        set_flash(request, f"Ejecución {run.status.lower()}: {run.summary}", "success" if run.status == "Ejecutado" else "warning")
        return RedirectResponse("/automatizaciones", status_code=303)

    @app.post("/automatizaciones/procesar-vencidas")
    def automations_process_due(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_automations")
        result = process_due_automations(session)
        set_flash(request, f"Programación revisada: {result['executed']} ejecuciones y {result['errors']} errores.")
        return RedirectResponse("/automatizaciones", status_code=303)
