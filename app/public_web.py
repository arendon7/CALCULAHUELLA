from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import CommercialLead, ServicePlan, get_db

_CONTACT_PLAN_LABELS = {
    "ESENCIAL": "Huella Esencial",
    "EMPRESARIAL": "Huella Empresarial",
    "CORPORATIVO": "Gestión Corporativa",
}
_ALLOWED_CONTACT_PLANS = {
    "Huella Esencial": "ESENCIAL",
    "Huella Empresarial": "EMPRESARIAL",
    "Gestión Corporativa": "CORPORATIVO",
    # Aliases históricos conservados para el handoff desde GitHub Pages.
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

FAIR_DISCOUNT_PERCENT = 30


def _fair_offer(plan: ServicePlan) -> dict[str, object]:
    """Build the public annual Feria offer without mutating billing semantics.

    The current campaign intentionally reuses the approved 390/990/2490
    commercial reference tiers as annual base values. ``ServicePlan`` keeps
    its historical monthly/annual fields unchanged for subscriptions and
    billing; only the public campaign presentation is transformed here.
    """

    regular_annual_fee = int(plan.monthly_fee or 0)
    promo_annual_fee = round(
        regular_annual_fee * (100 - FAIR_DISCOUNT_PERCENT) / 100
    )
    return {
        "plan": plan,
        "regular_annual_fee": regular_annual_fee,
        "promo_annual_fee": promo_annual_fee,
        "discount_percent": FAIR_DISCOUNT_PERCENT,
    }


def _query_choice(request: Request, name: str, allowed: set[str] | dict[str, str], fallback: str = "") -> str:
    value = request.query_params.get(name, "").strip()
    return value if value in allowed else fallback


def _normalize_contact_plan(value: str) -> tuple[str, str]:
    """Resolve any approved public/legacy label to canonical code + current label."""

    code = _ALLOWED_CONTACT_PLANS.get((value or "").strip(), "")
    return code, _CONTACT_PLAN_LABELS.get(code, "")


def _query_sites(request: Request) -> int | None:
    raw = request.query_params.get("sites", "").strip()
    if not raw:
        return None
    try:
        return max(1, min(100, int(raw)))
    except ValueError:
        return None


def _clean_form_value(form, name: str, default: str = "") -> str:
    value = form.get(name, default)
    return str(value).strip() if value is not None else default


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
        fair_offers = [_fair_offer(plan) for plan in plans]
        return templates.TemplateResponse(
            request=request,
            name="public_home.html",
            context={
                "user": user,
                "app_settings": settings,
                "plans": plans,
                "fair_offers": fair_offers,
                "fair_discount_percent": FAIR_DISCOUNT_PERCENT,
                "contact_sent": request.query_params.get("contacto") == "recibido",
            },
        )

    @app.api_route("/contacto", methods=["GET", "POST"], response_class=HTMLResponse)
    async def public_contact(request: Request, session: Session = Depends(get_db)):
        if request.method == "GET":
            raw_plan = _query_choice(request, "plan", _ALLOWED_CONTACT_PLANS)
            _, current_plan_label = _normalize_contact_plan(raw_plan)
            route_context = {
                "plan": current_plan_label,
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

        form = await request.form()
        company_name = _clean_form_value(form, "company_name")
        contact_name = _clean_form_value(form, "contact_name")
        normalized_email = _clean_form_value(form, "email").lower()
        phone = _clean_form_value(form, "phone")
        normalized_sector = _clean_form_value(form, "sector")
        normalized_interest = _clean_form_value(form, "interest", "Quiero entender por dónde comenzar")
        message = _clean_form_value(form, "message")
        accept_privacy = _clean_form_value(form, "accept_privacy")
        accept_commercial = _clean_form_value(form, "accept_commercial")

        if (
            "@" not in normalized_email
            or len(company_name) < 2
            or len(contact_name) < 2
            or len(message) < 12
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
        plan_code, current_plan_label = _normalize_contact_plan(normalized_interest)
        if plan_code:
            normalized_interest = current_plan_label
        if normalized_sector not in _ALLOWED_SECTORS:
            normalized_sector = "Por definir"

        lead = CommercialLead(
            public_token=secrets.token_urlsafe(24),
            company_name=company_name,
            contact_name=contact_name,
            email=normalized_email,
            phone=phone,
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
                f"{message}"
            ),
            complexity_score=0,
            recommended_plan_code=plan_code,
            status="Nuevo",
            source="Contacto público same-origin",
        )
        session.add(lead)
        session.commit()
        return RedirectResponse("/contacto?estado=recibido", status_code=303)
