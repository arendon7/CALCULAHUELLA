from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .period_close import close_period, period_close_summary, reopen_period, submit_period_close


def register_period_close_routes(app, templates, common_context, require_user, set_flash) -> None:
    def _can_view(user: dict) -> bool:
        return bool({"provide_data", "manage_inventory", "review", "approve", "view_methodology"} & set(user["capabilities"]))

    @app.get("/cierre-mensual", response_class=HTMLResponse)
    def monthly_close_page(
        request: Request,
        period: str | None = None,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not _can_view(user):
            raise HTTPException(403, "Tu rol no puede consultar el cierre mensual")
        try:
            summary = period_close_summary(session, int(user["organization_id"]), period)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        capabilities = set(user["capabilities"])
        context = common_context(
            request,
            session,
            user,
            "period_close",
            summary=summary,
            can_submit=bool({"provide_data", "manage_inventory"} & capabilities),
            can_close=bool({"review", "approve"} & capabilities),
            can_reopen="approve" in capabilities,
        )
        inventory = summary.get("inventory")
        if inventory is not None:
            context["inventory"] = inventory
        return templates.TemplateResponse(
            request=request,
            name="period_close.html",
            context=context,
        )

    @app.post("/cierre-mensual/enviar")
    def submit_close(
        request: Request,
        period: str = Form(...),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"provide_data", "manage_inventory"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede enviar periodos a revisión")
        try:
            record = submit_period_close(session, int(user["organization_id"]), period, str(user["email"]), notes)
            session.commit()
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "warning")
            return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)
        set_flash(request, f"Periodo {period} enviado a revisión. Estado: {record.status}.")
        return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)

    @app.post("/cierre-mensual/cerrar")
    def finalize_close(
        request: Request,
        period: str = Form(...),
        comments: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"review", "approve"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede cerrar periodos")
        try:
            record = close_period(session, int(user["organization_id"]), period, str(user["email"]), comments)
            session.commit()
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "warning")
            return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)
        set_flash(request, f"Periodo cerrado con hash {record.snapshot_hash[:12]}…")
        return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)

    @app.post("/cierre-mensual/reabrir")
    def reopen_close(
        request: Request,
        period: str = Form(...),
        reason: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if "approve" not in set(user["capabilities"]):
            raise HTTPException(403, "Solo el rol aprobador puede reabrir periodos")
        try:
            record = reopen_period(session, int(user["organization_id"]), period, str(user["email"]), reason)
            session.commit()
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "warning")
            return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)
        set_flash(request, f"Periodo {period} reabierto. Motivo registrado en auditoría.", "warning")
        return RedirectResponse(f"/cierre-mensual?period={period}", status_code=303)
