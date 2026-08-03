from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .access_control import ROLE_CAPABILITIES
from .database import (
    AppUser,
    OrganizationMembership,
    add_audit,
    get_db,
    hash_password,
)


def register_user_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
) -> None:
    @app.get("/usuarios", response_class=HTMLResponse)
    def users_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_org")
        memberships = list(session.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == int(user["organization_id"]))
            .options(selectinload(OrganizationMembership.user))
            .order_by(OrganizationMembership.active.desc(), OrganizationMembership.id)
        ))
        roles = ["Administrador", "Consultor", "Cliente", "Revisor", "Verificador"]
        return templates.TemplateResponse(request=request, name="users.html", context=common_context(request, session, user, "users", memberships=memberships, roles=roles))

    @app.post("/usuarios/nuevo")
    def create_user(request: Request, name: str = Form(...), email: str = Form(...), role: str = Form(...), password: str = Form("Demo2026!"), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_org")
        normalized_email = email.strip().lower()
        if role not in ROLE_CAPABILITIES:
            raise HTTPException(400, "Rol inválido")
        if len(password) < 8:
            raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
        target = session.scalar(select(AppUser).where(AppUser.email == normalized_email))
        if not target:
            target = AppUser(organization_id=int(user["organization_id"]), name=name.strip(), email=normalized_email, role=role, password_hash=hash_password(password), active=True)
            session.add(target)
            session.flush()
        existing_membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == target.id, OrganizationMembership.organization_id == int(user["organization_id"])
        ))
        if existing_membership:
            raise HTTPException(409, "El usuario ya pertenece a esta organización")
        session.add(OrganizationMembership(user_id=target.id, organization_id=int(user["organization_id"]), role=role, active=True))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ASIGNAR", "Usuario", normalized_email, f"Rol {role}")
        session.commit()
        set_flash(request, "Usuario vinculado correctamente a la organización.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/estado")
    def toggle_user_status(user_id: int, request: Request, active: bool = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_org")
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id, OrganizationMembership.organization_id == int(user["organization_id"])
        ).options(selectinload(OrganizationMembership.user)))
        if not membership:
            raise HTTPException(404, "Usuario no encontrado en esta organización")
        if membership.user_id == int(user["id"]) and not active:
            raise HTTPException(409, "No puedes desactivar tu propia membresía")
        membership.active = active
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTIVAR" if active else "DESACTIVAR", "Membresía", membership.user.email, f"Rol {membership.role}")
        session.commit()
        set_flash(request, "Acceso a la organización actualizado.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/restablecer")
    def reset_user_password(user_id: int, request: Request, password: str = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_org")
        if len(password) < 8:
            raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id, OrganizationMembership.organization_id == int(user["organization_id"])
        ).options(selectinload(OrganizationMembership.user)))
        if not membership:
            raise HTTPException(404, "Usuario no encontrado en esta organización")
        membership.user.password_hash = hash_password(password)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RESTABLECER", "Usuario", membership.user.email, "Contraseña actualizada")
        session.commit()
        set_flash(request, "Contraseña restablecida.")
        return RedirectResponse("/usuarios", status_code=303)

