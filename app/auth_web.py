from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from .config import settings
from .database import AppUser, SessionLocal, add_audit, hash_password
from .security import login_throttle, password_needs_upgrade, verify_password


def register_auth_routes(app, templates, current_user) -> None:
    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        existing_user = current_user(request)
        if existing_user:
            return RedirectResponse(
                "/verificacion" if existing_user["role"] == "Verificador" else "/dashboard",
                status_code=303,
            )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": None, "app_settings": settings},
        )

    @app.post("/login", response_class=HTMLResponse)
    def login(request: Request, email: str = Form(...), password: str = Form(...)):
        normalized_email = email.strip().lower()
        client_ip = request.client.host if request.client else "unknown"
        throttle = login_throttle.status(normalized_email, client_ip)
        if throttle.blocked:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "error": f"Demasiados intentos. Intenta nuevamente en {throttle.retry_after} segundos.",
                    "app_settings": settings,
                },
                status_code=429,
                headers={"Retry-After": str(throttle.retry_after)},
            )

        with SessionLocal() as session:
            db_user = session.scalar(
                select(AppUser).where(
                    AppUser.email == normalized_email,
                    AppUser.active.is_(True),
                )
            )
            valid = db_user is not None and verify_password(password, db_user.password_hash)
            if not valid:
                blocked = login_throttle.failure(normalized_email, client_ip)
                message = "Credenciales incorrectas." + (
                    " Usa uno de los usuarios demostrativos." if settings.seed_demo else ""
                )
                status_code = 400
                headers = None
                if blocked.blocked:
                    message = (
                        "Acceso bloqueado temporalmente por seguridad. "
                        f"Intenta en {blocked.retry_after} segundos."
                    )
                    status_code = 429
                    headers = {"Retry-After": str(blocked.retry_after)}
                return templates.TemplateResponse(
                    request=request,
                    name="login.html",
                    context={"error": message, "app_settings": settings},
                    status_code=status_code,
                    headers=headers,
                )
            if password_needs_upgrade(db_user.password_hash):
                db_user.password_hash = hash_password(password)
            db_user.last_login = datetime.now(UTC)
            add_audit(
                session,
                db_user.organization_id,
                db_user.email,
                "LOGIN",
                "Sesión",
                client_ip,
                "Acceso exitoso",
            )
            session.commit()
            organization_id = db_user.organization_id
            role = db_user.role

        login_throttle.success(normalized_email, client_ip)
        request.session.clear()
        request.session["user_email"] = normalized_email
        request.session["active_org_id"] = organization_id
        return RedirectResponse(
            "/verificacion" if role == "Verificador" else "/dashboard",
            status_code=303,
        )

    @app.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)
