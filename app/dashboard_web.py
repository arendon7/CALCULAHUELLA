from __future__ import annotations

from typing import Any

from fastapi import Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_request_status import CLOSED_DATA_REQUEST_STATUSES
from .database import get_db
from .db.models import CustomerOnboardingItem, DataRequest, Inventory
from .delivery_readiness import professional_delivery_summary
from .guided_onboarding import load_profile as load_guided_profile, decision_plan as guided_decision_plan
from .onboarding_experience import onboarding_summary
from .pilot_execution import guided_workspace
from .product_experience import demo_story_for, journey_detail, normalize_view_mode


def resolve_dashboard_action(
    role: str,
    tasks: list[DataRequest],
    delivery: dict[str, Any],
) -> dict[str, Any] | None:
    """Keep Cliente on data work only while data work is genuinely pending."""
    base_action = delivery.get("next_action")
    if role != "Cliente":
        return base_action
    if tasks:
        return {
            "name": "Atender solicitudes de información",
            "detail": f"Tienes {len(tasks)} requerimiento(s) activo(s). Completa los datos o soportes solicitados antes de la revisión técnica.",
            "owner": "Responsable de información",
            "acceptance": "Solicitudes respondidas y evidencias vinculadas al periodo correcto.",
            "href": "/informacion#solicitudes",
            "action": "Abrir pendientes",
        }
    activity_gate = next(
        (gate for gate in delivery.get("gates", []) if gate.get("code") == "activity"),
        None,
    )
    if not activity_gate or activity_gate.get("status") != "Listo":
        return {
            "name": "Completar datos y evidencias",
            "detail": "Revisa los periodos pendientes y conserva un soporte verificable para cada valor relevante.",
            "owner": "Responsable de información",
            "acceptance": "Fuentes del periodo completas y soportes vinculados.",
            "href": "/captura-guiada",
            "action": "Continuar captura",
        }
    return base_action


def register_dashboard_routes(
    app, templates, common_context, require_user, set_flash, get_inventory, inventory_metrics
) -> None:
    @app.post("/preferencias/vista")
    def update_view_mode(
        request: Request,
        mode: str = Form(...),
        return_url: str = Form("/dashboard"),
        user: dict = Depends(require_user),
    ):
        request.session["view_mode"] = normalize_view_mode(mode)
        destination = return_url if return_url.startswith("/") and not return_url.startswith("//") else "/dashboard"
        set_flash(
            request,
            "Vista esencial activada: se prioriza el flujo del inventario."
            if request.session["view_mode"] == "essential"
            else "Vista completa activada: se muestran capacidades avanzadas e internas.",
        )
        return RedirectResponse(destination, status_code=303)

    @app.get("/recorrido-inventario", response_class=HTMLResponse)
    def inventory_journey_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        workspace = guided_workspace(session, user, inventory)
        journey = journey_detail(workspace, str(user["role"]))
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="inventory_journey.html",
            context=common_context(
                request,
                session,
                user,
                "journey",
                inventory=inventory,
                journey=journey,
            ),
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        metrics = inventory_metrics(inventory)
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
        tasks = list(session.scalars(
            select(DataRequest)
            .where(
                DataRequest.inventory_id == inventory.id,
                DataRequest.status.notin_(tuple(CLOSED_DATA_REQUEST_STATUSES)),
            )
            .order_by(DataRequest.due_date)
        ))
        workspace = guided_workspace(session, user, inventory)
        delivery = professional_delivery_summary(session, inventory)
        dashboard_action = resolve_dashboard_action(str(user["role"]), tasks, delivery)
        onboarding_rows = list(session.scalars(select(CustomerOnboardingItem).where(
            CustomerOnboardingItem.organization_id == int(user["organization_id"])
        ).order_by(CustomerOnboardingItem.display_order)))
        onboarding_state = onboarding_summary(onboarding_rows, inventory_id=inventory.id)
        guided_profile = load_guided_profile(session, inventory.organization)
        guided_setup = guided_decision_plan(guided_profile, inventory.organization, inventory=inventory)
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=common_context(
                request, session, user, "dashboard", inventory=inventory, inventories=inventories,
                tasks=tasks, sources=inventory.sources, workspace=workspace, delivery=delivery,
                dashboard_action=dashboard_action,
                journey=journey_detail(workspace, str(user["role"])), onboarding=onboarding_state,
                guided_setup=guided_setup, demo_story=demo_story_for(inventory.organization.trade_name), **metrics,
            ),
        )
