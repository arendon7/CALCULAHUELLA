from __future__ import annotations

import re

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .database import add_audit, get_db
from .db.models import AppUser, Notification, OrganizationMembership, PlatformSetting
from .notifications import notify_roles, process_pending_notifications
from .storage import storage


INTERNAL_PLATFORM_SETTING_PREFIX = "runtime_internal_"


def register_platform_admin_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/administracion-plataforma", response_class=HTMLResponse)
    def platform_admin_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_operations")
        users = list(session.scalars(
            select(AppUser).join(OrganizationMembership).where(
                OrganizationMembership.organization_id == int(user["organization_id"]),
                OrganizationMembership.active.is_(True),
            ).order_by(AppUser.name)
        ))
        settings_rows = [
            row
            for row in session.scalars(
                select(PlatformSetting)
                .where(PlatformSetting.organization_id == int(user["organization_id"]))
                .order_by(PlatformSetting.key)
            )
            if not row.key.startswith(INTERNAL_PLATFORM_SETTING_PREFIX)
        ]
        notification_stats = {
            "total": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]))) or 0,
            "pending": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]), Notification.status.in_(["Pendiente", "Error"]))) or 0,
            "unread": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]), Notification.read_at.is_(None))) or 0,
        }
        storage_status = storage.diagnostics()
        return templates.TemplateResponse(
            request=request,
            name="platform_admin.html",
            context=common_context(request, session, user, "platform_admin", users=users, settings_rows=settings_rows, notification_stats=notification_stats, storage_status=storage_status, app_settings=settings),
        )

    @app.post("/administracion-plataforma/configuracion")
    def platform_setting_update(
        request: Request,
        key: str = Form(...),
        value: str = Form(...),
        description: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        clean_key = re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_")
        if not clean_key:
            raise HTTPException(400, "Clave inválida")
        if clean_key.startswith(INTERNAL_PLATFORM_SETTING_PREFIX):
            raise HTTPException(400, "Clave reservada para el runtime")
        row = session.scalar(select(PlatformSetting).where(PlatformSetting.organization_id == int(user["organization_id"]), PlatformSetting.key == clean_key))
        if not row:
            row = PlatformSetting(organization_id=int(user["organization_id"]), key=clean_key)
            session.add(row)
        row.value = value.strip()
        row.description = description.strip()
        row.updated_by = str(user["email"])
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CONFIGURAR", "Plataforma", clean_key, value.strip())
        session.commit()
        set_flash(request, "Configuración guardada.")
        return RedirectResponse("/administracion-plataforma", status_code=303)

    @app.post("/administracion-plataforma/notificaciones/prueba")
    def platform_test_notification(
        request: Request,
        role: str = Form("Administrador"),
        title: str = Form("Prueba de notificación"),
        message: str = Form("El centro de notificaciones está operativo."),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        created = notify_roles(session, int(user["organization_id"]), {role}, title, message, link="/notificaciones", category="Prueba", email_requested=True)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "NOTIFICAR", "Plataforma", role, f"{len(created)} destinatarios")
        session.commit()
        set_flash(request, f"Se generaron {len(created)} notificaciones de prueba.")
        return RedirectResponse("/administracion-plataforma", status_code=303)

    @app.post("/administracion-plataforma/notificaciones/procesar")
    def platform_process_notifications(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_operations")
        result = process_pending_notifications(session, settings.notification_batch_size)
        session.commit()
        set_flash(request, f"Cola procesada: {result['sent']} enviadas y {result['failed']} con error.")
        return RedirectResponse("/administracion-plataforma", status_code=303)
