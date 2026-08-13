from __future__ import annotations

import secrets

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import CommercialLead, ServicePlan, get_db

_ALLOWED_CONTACT_PLANS = {
    "Huella Esencial": "ESENCIAL",
    "Gestión de Carbono": "EMPRESARIAL",
    "Gestión Avanzada": "CORPORATIVO",
    "Gestión Avanzada y Verificación": "CORPORATIVO",
}
_ALLOWED_SECTORS = {
    "Servicios y oficinas",
    "Industria o manufactura",
    "Agroindustria",
    "Transporte y logística",
    "Gestión de residuos",
}
_ALLOWED_OBJECTIVES = {
    "Construir la primera huella",
    "Responder a cliente o licitación",
    "Gestionar un plan de reducción",
    "Preparar revisión externa",
}


def _query_choice(request: Request, name: str, allowed: set[str] | dict[str, str], fallback: str = "") -> str:
    value = request.query_params.get(name, "").strip()
    return value if value in allowed else fallback


def _query_sites(request: Request) -> int | None:
    raw = request.query_params.get("sites", "").strip()
    if not raw:
        return None
    try:
        return max(1, min(100, int(raw)))
    except ValueError:
        return None


def register_public_routes(app, templates, current_user) -> None:
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, session: Session = Depends(get_db)):
        user = current_user(request)
        plans = list(
            session.scalars(
                select(ServicePlan)
                .where(ServicePlan.active.is_(True))
                .order_by(ServicePlan.monthly_fee)
            )
        )
        return templates.TemplateResponse(
            request=request,
            name="public_home.html",
            context={
                "user": user,
                "app_settings": settings,
                "plans": plans,
                "contact_sent": request.query_params.get("contacto") == "recibido",
            },
        )

    @app.get("/contacto", response_class=HTMLResponse)
    def public_contact_form(request: Request):
        route_context = {
            "plan": _query_choice(request, "plan", _ALLOWED_CONTACT_PLANS),
            "sector": _query_choice(request, "sector", _ALLOWED_SECTORS),
            "sites": _query_sites(request),
            "objective": _query_choice(request, "objective", _ALLOWED_OBJECTIVES),
        }
        return templates.TemplateResponse(
            request=request,
            name="public_contact.html",
            context={
                "user": current_user(request),
                "app_settings": settings,
                "route_context": route_context,
                "contact_sent": request.query_params.get("estado") == "recibido",
            },
        )

    @app.post("/contacto")
    def public_contact_request(
        request: Request,
        company_name: str = Form(...),
        contact_name: str = Form(...),
        email: str = Form(...),
        phone: str = Form(""),
        sector: str = Form(""),
        interest: str = Form("Quiero entender por dónde comenzar"),
        message: str = Form(...),
        accept_privacy: str | None = Form(None),
        accept_commercial: str | None = Form(None),
        session: Session = Depends(get_db),
    ):
        normalized_email = email.strip().lower()
        normalized_interest = interest.strip()
        normalized_sector = sector.strip()
        if (
            "@" not in normalized_email
            or len(company_name.strip()) < 2
            or len(contact_name.strip()) < 2
            or len(message.strip()) < 12
        ):
            raise HTTPException(
                400,
                "Completa empresa, contacto, correo válido y una descripción suficiente.",
            )
        if accept_privacy != "yes":
            raise HTTPException(
                400,
                "Debes autorizar el tratamiento de datos para responder la solicitud.",
            )
        if normalized_interest not in _ALLOWED_CONTACT_PLANS:
            normalized_interest = "Quiero entender por dónde comenzar"
        if normalized_sector not in _ALLOWED_SECTORS:
            normalized_sector = "Por definir"
        lead = CommercialLead(
            public_token=secrets.token_urlsafe(24),
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            email=normalized_email,
            phone=phone.strip(),
            sector=normalized_sector,
            city="",
            employees_band="Por definir",
            facilities_count=1,
            has_previous_inventory=False,
            desired_scopes="Por definir",
            objective=normalized_interest,
            urgency="Normal",
            notes=(
                f"Solicitud desde contacto público same-origin\n"
                f"Autorización de privacidad: sí · versión {settings.legal_effective_date}\n"
                f"Comunicaciones comerciales opcionales: {'sí' if accept_commercial == 'yes' else 'no'}\n\n"
                f"{message.strip()}"
            ),
            complexity_score=0,
            recommended_plan_code=_ALLOWED_CONTACT_PLANS.get(normalized_interest, ""),
            status="Nuevo",
            source="Contacto público same-origin",
        )
        session.add(lead)
        session.commit()
        return RedirectResponse("/contacto?estado=recibido", status_code=303)
