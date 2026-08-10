from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .db.models import Notification
from .notifications import get_or_create_preference


def register_notification_routes(
    app, templates, common_context, require_user, set_flash
) -> None:
    @app.get("/notificaciones", response_class=HTMLResponse)
    def notifications_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        notifications = list(session.scalars(select(Notification).where(
            Notification.organization_id == int(user["organization_id"]),
            Notification.user_id == int(user["id"]),
        ).order_by(Notification.created_at.desc()).limit(100)))
        preference = get_or_create_preference(session, int(user["id"]))
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="notifications.html",
            context=common_context(request, session, user, "notifications", notifications=notifications, preference=preference),
        )

    @app.post("/notificaciones/{notification_id}/leer")
    def notification_read(notification_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        notification = session.scalar(select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == int(user["organization_id"]),
            Notification.user_id == int(user["id"]),
        ))
        if not notification:
            raise HTTPException(404, "Notificación no encontrada")
        notification.read_at = datetime.now(UTC)
        session.commit()
        return RedirectResponse(notification.link or "/notificaciones", status_code=303)

    @app.post("/notificaciones/leer-todas")
    def notifications_read_all(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        notifications = list(session.scalars(select(Notification).where(
            Notification.organization_id == int(user["organization_id"]),
            Notification.user_id == int(user["id"]),
            Notification.read_at.is_(None),
        )))
        now = datetime.now(UTC)
        for notification in notifications:
            notification.read_at = now
        session.commit()
        set_flash(request, "Todas las notificaciones quedaron marcadas como leídas.")
        return RedirectResponse("/notificaciones", status_code=303)

    @app.post("/notificaciones/preferencias")
    def notification_preferences_update(
        request: Request,
        email_enabled: str | None = Form(None),
        in_app_enabled: str | None = Form(None),
        digest_frequency: str = Form("Inmediato"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        preference = get_or_create_preference(session, int(user["id"]))
        preference.email_enabled = email_enabled == "on"
        preference.in_app_enabled = in_app_enabled == "on"
        preference.digest_frequency = digest_frequency if digest_frequency in {"Inmediato", "Diario", "Semanal"} else "Inmediato"
        session.commit()
        set_flash(request, "Preferencias de notificación actualizadas.")
        return RedirectResponse("/notificaciones", status_code=303)
