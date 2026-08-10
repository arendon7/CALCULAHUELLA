from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import BillingInvoice, Organization, OrganizationSubscription, ServicePlan


def register_saas_admin_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
) -> None:
    @app.get("/administracion-saas", response_class=HTMLResponse)
    def saas_admin(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ensure_capability(user, "manage_saas")
        plans = list(session.scalars(select(ServicePlan).order_by(ServicePlan.monthly_fee)))
        subscriptions = list(session.scalars(
            select(OrganizationSubscription)
            .options(selectinload(OrganizationSubscription.organization), selectinload(OrganizationSubscription.plan))
            .order_by(OrganizationSubscription.id)
        ))
        invoices = list(session.scalars(select(BillingInvoice).order_by(BillingInvoice.issued_at.desc()).limit(50)))
        organizations = list(session.scalars(select(Organization).order_by(Organization.name)))
        summary = {
            "active": sum(1 for item in subscriptions if item.status == "Activa"),
            "trial": sum(1 for item in subscriptions if item.status == "Prueba"),
            "mrr": round(sum((item.custom_monthly_fee or (item.plan.monthly_fee if item.plan else 0)) for item in subscriptions if item.status in {"Activa", "Prueba"})),
            "organizations": len(organizations),
        }
        return templates.TemplateResponse(request, "saas_admin.html", common_context(
            request, session, user, "saas_admin", plans=plans, subscriptions=subscriptions,
            invoices=invoices, organizations=organizations, summary=summary,
        ))

    @app.post("/administracion-saas/planes/nuevo")
    def create_service_plan(
        request: Request,
        code: str = Form(...), name: str = Form(...), description: str = Form(""),
        monthly_fee: float = Form(0), annual_fee: float = Form(0),
        max_users: int = Form(5), max_facilities: int = Form(3), max_inventories: int = Form(3), max_storage_mb: int = Form(1024),
        includes_scope3: str | None = Form(None), includes_verification_portal: str | None = Form(None),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_saas")
        normalized_code = re.sub(r"[^A-Z0-9_-]", "", code.upper())
        if not normalized_code or session.scalar(select(ServicePlan).where(ServicePlan.code == normalized_code)):
            raise HTTPException(400, "Código de plan inválido o duplicado")
        plan = ServicePlan(
            code=normalized_code, name=name.strip(), description=description.strip(), monthly_fee=max(0, monthly_fee), annual_fee=max(0, annual_fee),
            max_users=max(1, max_users), max_facilities=max(1, max_facilities), max_inventories=max(1, max_inventories), max_storage_mb=max(100, max_storage_mb),
            includes_scope3=bool(includes_scope3), includes_verification_portal=bool(includes_verification_portal), active=True,
        )
        session.add(plan)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Plan SaaS", plan.name, detail=plan.code)
        session.commit()
        set_flash(request, f"Plan {plan.name} creado.")
        return RedirectResponse("/administracion-saas", status_code=303)

    @app.post("/administracion-saas/suscripciones/{subscription_id}/actualizar")
    def admin_update_subscription(
        subscription_id: int,
        request: Request,
        plan_id: int = Form(...), status: str = Form(...), billing_cycle: str = Form("Anual"),
        custom_monthly_fee: str = Form(""), renewal_date: str = Form(""), notes: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_saas")
        subscription = session.get(OrganizationSubscription, subscription_id)
        plan = session.get(ServicePlan, plan_id)
        if not subscription or not plan:
            raise HTTPException(404, "Suscripción o plan no encontrado")
        subscription.plan_id = plan.id
        subscription.status = status if status in {"Prueba", "Activa", "Suspendida", "Cancelada"} else subscription.status
        subscription.billing_cycle = billing_cycle if billing_cycle in {"Mensual", "Anual"} else subscription.billing_cycle
        subscription.custom_monthly_fee = float(custom_monthly_fee) if custom_monthly_fee.strip() else None
        subscription.renewal_date = parse_date(renewal_date) if renewal_date else None
        subscription.notes = notes.strip()
        session.commit()
        set_flash(request, f"Suscripción de {subscription.organization.name} actualizada.")
        return RedirectResponse("/administracion-saas", status_code=303)

    @app.post("/administracion-saas/facturas/{invoice_id}/estado")
    def update_invoice_status(
        invoice_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_saas")
        invoice = session.get(BillingInvoice, invoice_id)
        if not invoice:
            raise HTTPException(404, "Registro de cobro no encontrado")
        invoice.status = status if status in {"Pendiente", "Pagada", "Vencida", "Anulada", "Demostrativa"} else invoice.status
        invoice.paid_at = datetime.now(UTC) if invoice.status == "Pagada" else None
        session.commit()
        set_flash(request, f"Estado de {invoice.reference} actualizado.")
        return RedirectResponse("/administracion-saas", status_code=303)
