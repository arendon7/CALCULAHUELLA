from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import add_audit, get_db
from .db.models import CommercialReadinessItem


def register_readiness_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
) -> None:
    @app.get("/alistamiento", response_class=HTMLResponse)
    def readiness_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_readiness")
        rows = list(session.scalars(select(CommercialReadinessItem).where(CommercialReadinessItem.organization_id == int(user["organization_id"])).order_by(CommercialReadinessItem.display_order)))
        weights = {"Completado": 100, "En progreso": 50, "Pendiente": 0, "Bloqueado": 0}
        score = round(sum(weights.get(row.status, 0) for row in rows) / max(len(rows), 1))
        categories = {}
        for row in rows:
            categories.setdefault(row.category, []).append(row)
        return templates.TemplateResponse(request=request, name="readiness.html", context=common_context(request, session, user, "readiness", rows=rows, categories=categories, readiness_score=score))

    @app.post("/alistamiento/{item_id}/actualizar")
    def readiness_update(item_id: int, request: Request, status: str = Form(...), owner: str = Form(...), due_date: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_readiness")
        row = session.scalar(select(CommercialReadinessItem).where(CommercialReadinessItem.id == item_id, CommercialReadinessItem.organization_id == int(user["organization_id"])))
        if not row:
            raise HTTPException(404, "Elemento no encontrado")
        if status not in {"Completado", "En progreso", "Pendiente", "Bloqueado"}:
            raise HTTPException(400, "Estado inválido")
        row.status = status
        row.owner = owner.strip()
        row.due_date = parse_date(due_date) if due_date else None
        row.notes = notes.strip()
        row.updated_by = str(user["email"])
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Alistamiento comercial", row.title, status)
        session.commit()
        set_flash(request, "Elemento de alistamiento actualizado.")
        return RedirectResponse("/alistamiento", status_code=303)
