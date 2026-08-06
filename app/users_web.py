from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .access_control import ROLE_CAPABILITIES
from .database import (
    AppUser,
    OrganizationMembership,
    UserInvitation,
    add_audit,
    get_db,
    hash_password,
)
from .service_operations import capacity_snapshot, create_invitation, ensure_invitation_acceptance, resolve_invitation


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
        organization_id = int(user["organization_id"])
        memberships = list(session.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .options(selectinload(OrganizationMembership.user))
            .order_by(OrganizationMembership.active.desc(), OrganizationMembership.id)
        ))
        capacity = capacity_snapshot(session, organization_id)
        roles = ["Administrador", "Consultor", "Cliente", "Revisor", "Verificador"]
        invitation_url = request.session.pop("last_invitation_url", "")
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="users.html",
            context=common_context(
                request,
                session,
                user,
                "users",
                memberships=memberships,
                roles=roles,
                invitations=capacity["pending_invitations"],
                capacity=capacity,
                invitation_url=invitation_url,
            ),
        )

    @app.post("/usuarios/invitar")
    def invite_user(
        request: Request,
        email: str = Form(...),
        role: str = Form(...),
        name: str = Form(""),
        validity_days: int = Form(7),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        if role not in ROLE_CAPABILITIES:
            raise HTTPException(400, "Rol inválido")
        invitation, token = create_invitation(
            session,
            int(user["organization_id"]),
            email=email,
            role=role,
            invited_by=str(user["email"]),
            name=name,
            days_valid=validity_days,
        )
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "INVITAR",
            "Usuario",
            invitation.email,
            detail=f"Rol {role}; vence {invitation.expires_at.date().isoformat()}",
        )
        session.commit()
        request.session["last_invitation_url"] = str(request.url_for("invitation_page", token=token))
        set_flash(request, "Invitación creada. Copia el enlace y compártelo únicamente con la persona autorizada.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/invitaciones/{invitation_id}/cancelar")
    def cancel_invitation(
        invitation_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        invitation = session.scalar(select(UserInvitation).where(
            UserInvitation.id == invitation_id,
            UserInvitation.organization_id == int(user["organization_id"]),
        ))
        if not invitation:
            raise HTTPException(404, "Invitación no encontrada")
        if invitation.status != "Pendiente":
            raise HTTPException(409, "La invitación ya no está pendiente")
        invitation.status = "Cancelada"
        invitation.cancelled_at = datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CANCELAR", "Invitación", invitation.email)
        session.commit()
        set_flash(request, "Invitación cancelada.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.get("/invitacion/{token}", response_class=HTMLResponse, name="invitation_page")
    def invitation_page(token: str, request: Request, session: Session = Depends(get_db)):
        invitation = resolve_invitation(session, token)
        valid = bool(invitation and invitation.status == "Pendiente")
        return templates.TemplateResponse(
            request=request,
            name="public_invitation.html",
            context={"request": request, "user": None, "invitation": invitation, "token": token, "valid": valid},
        )

    @app.post("/invitacion/{token}/aceptar")
    def accept_invitation(
        token: str,
        request: Request,
        name: str = Form(""),
        password: str = Form(""),
        session: Session = Depends(get_db),
    ):
        invitation = resolve_invitation(session, token)
        if not invitation or invitation.status != "Pendiente":
            raise HTTPException(409, "La invitación no está disponible")
        ensure_invitation_acceptance(session, invitation.organization_id)
        target = session.scalar(select(AppUser).where(AppUser.email == invitation.email))
        if not target:
            final_name = name.strip() or invitation.invited_name.strip()
            if not final_name:
                raise HTTPException(400, "Indica tu nombre completo")
            if len(password) < 8:
                raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
            target = AppUser(
                organization_id=invitation.organization_id,
                name=final_name,
                email=invitation.email,
                role=invitation.role,
                password_hash=hash_password(password),
                active=True,
            )
            session.add(target)
            session.flush()
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == target.id,
            OrganizationMembership.organization_id == invitation.organization_id,
        ))
        if membership:
            membership.active = True
            membership.role = invitation.role
        else:
            session.add(OrganizationMembership(
                user_id=target.id,
                organization_id=invitation.organization_id,
                role=invitation.role,
                active=True,
            ))
        invitation.status = "Aceptada"
        invitation.accepted_at = datetime.now(UTC)
        add_audit(
            session,
            invitation.organization_id,
            invitation.email,
            "ACEPTAR",
            "Invitación",
            invitation.email,
            detail=f"Rol {invitation.role}",
        )
        session.commit()
        request.session["user_email"] = target.email
        request.session["organization_id"] = invitation.organization_id
        return RedirectResponse("/dashboard", status_code=303)

    @app.post("/usuarios/nuevo")
    def create_user(request: Request, name: str = Form(...), email: str = Form(...), role: str = Form(...), password: str = Form("Demo2026!"), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_org")
        normalized_email = email.strip().lower()
        if role not in ROLE_CAPABILITIES:
            raise HTTPException(400, "Rol inválido")
        if len(password) < 8:
            raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
        # La creación directa se conserva para administración local, pero respeta la capacidad del plan.
        from .service_operations import ensure_capacity
        ensure_capacity(session, int(user["organization_id"]), "users", 1)
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
        if active and not membership.active:
            from .service_operations import ensure_capacity
            ensure_capacity(session, int(user["organization_id"]), "users", 1)
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
