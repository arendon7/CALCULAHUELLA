from __future__ import annotations

import secrets

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import CommercialLead, ServicePlan, get_db


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
        plan_map = {
            "Huella Esencial": "ESENCIAL",
            "Gestión de Carbono": "EMPRESARIAL",
            "Gestión Avanzada y Verificación": "CORPORATIVO",
        }
        lead = CommercialLead(
            public_token=secrets.token_urlsafe(24),
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            email=normalized_email,
            phone=phone.strip(),
            sector=sector.strip() or "Por definir",
            city="",
            employees_band="Por definir",
            facilities_count=1,
            has_previous_inventory=False,
            desired_scopes="Por definir",
            objective=interest.strip(),
            urgency="Normal",
            notes=(
                f"Solicitud desde landing V1.0\n"
                f"Autorización de privacidad: sí · versión {settings.legal_effective_date}\n"
                f"Comunicaciones comerciales opcionales: {'sí' if accept_commercial == 'yes' else 'no'}\n\n"
                f"{message.strip()}"
            ),
            complexity_score=0,
            recommended_plan_code=plan_map.get(interest.strip(), ""),
            status="Nuevo",
            source="Landing pública V1.0",
        )
        session.add(lead)
        session.commit()
        return RedirectResponse("/?contacto=recibido#contacto", status_code=303)
