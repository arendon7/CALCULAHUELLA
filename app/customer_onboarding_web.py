from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import add_audit, get_db
from .db.models import CustomerOnboardingItem
from .onboarding_experience import onboarding_summary


def register_customer_onboarding_routes(
    app, templates, common_context, require_user, set_flash, parse_date, get_inventory
) -> None:
    @app.get("/onboarding", response_class=HTMLResponse)
    def onboarding(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        inventory = get_inventory(session, user)
        rows = list(session.scalars(select(CustomerOnboardingItem).where(
            CustomerOnboardingItem.organization_id == int(user["organization_id"])
        ).order_by(CustomerOnboardingItem.display_order)))
        onboarding_state = onboarding_summary(rows, inventory_id=inventory.id)
        return templates.TemplateResponse(request, "onboarding.html", common_context(
            request, session, user, "onboarding", inventory=inventory, rows=rows,
            onboarding=onboarding_state, onboarding_score=onboarding_state["score"],
        ))

    @app.post("/onboarding/{item_id}/actualizar")
    def update_onboarding_item(
        item_id: int,
        request: Request,
        status: str = Form(...),
        owner: str = Form(""),
        due_date: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        if not (user["can_manage_org"] or user["can_manage_inventory"]):
            raise HTTPException(403, "Tu rol no puede modificar el onboarding")
        row = session.scalar(select(CustomerOnboardingItem).where(
            CustomerOnboardingItem.id == item_id,
            CustomerOnboardingItem.organization_id == int(user["organization_id"]),
        ))
        if not row:
            raise HTTPException(404, "Actividad de onboarding no encontrada")
        row.status = status if status in {"Pendiente", "En progreso", "Completado", "Bloqueado"} else "Pendiente"
        row.owner = owner.strip() or row.owner
        row.due_date = parse_date(due_date) if due_date else None
        row.completed_at = datetime.now(UTC) if row.status == "Completado" else None
        row.updated_by = str(user["email"])
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Onboarding", row.title, new_value=row.status)
        session.commit()
        set_flash(request, "Actividad de onboarding actualizada.")
        return RedirectResponse("/onboarding", status_code=303)
