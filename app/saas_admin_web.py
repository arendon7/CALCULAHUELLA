from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import BillingInvoice, Organization, OrganizationSubscription, ServicePlan
from .money import parse_money, parse_recurring_basis, quantize_money


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
        mrr = sum(
            (
                item.custom_monthly_fee
                if item.custom_monthly_fee is not None
                else (item.plan.monthly_fee if item.plan else Decimal("0"))
                for item in subscriptions
                if item.status in {"Activa", "Prueba"}
            ),
            Decimal("0"),
        )
        summary = {
            "active": sum(1 for item in subscriptions if item.status == "Activa"),
            "trial": sum(1 for item in subscriptions if item.status == "Prueba"),
            "mrr": quantize_money(mrr),
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
        monthly_fee: str = Form("0"), annual_fee: str = Form("0"),
        max_users: int = Form(5), max_facilities: int = Form(3), max_inventories: int = Form(3), max_storage_mb: int = Form(1024),
        includes_scope3: str | None = Form(None), includes_verification_portal: str | None = Form(None),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_saas")
        normalized_code = re.sub(r"[^A-Z0-9_-]", "", code.upper())
        if not normalized_code or session.scalar(select(ServicePlan).where(ServicePlan.code == normalized_code)):
            raise HTTPException(400, "Código de plan inválido o duplicado")
        try:
            monthly_value = parse_money(monthly_fee, "el valor mensual del plan")
            annual_value = parse_money(annual_fee, "el valor anual del plan")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        plan = ServicePlan(
            code=normalized_code, name=name.strip(), description=description.strip(),
            monthly_fee=monthly_value, annual_fee=annual_value,
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
        if status not in {"Prueba", "Activa", "Suspendida", "Cancelada"}:
            raise HTTPException(400, "Estado de suscripción inválido")
        if billing_cycle not in {"Mensual", "Anual"}:
            raise HTTPException(400, "Ciclo de facturación inválido")
        try:
            custom_fee = parse_recurring_basis(custom_monthly_fee, "la base mensual personalizada") if custom_monthly_fee.strip() else None
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        subscription.plan_id = plan.id
        subscription.status = status
        subscription.billing_cycle = billing_cycle
        subscription.custom_monthly_fee = custom_fee
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
        if status not in {"Pendiente", "Pagada", "Vencida", "Anulada", "Demostrativa"}:
            raise HTTPException(400, "Estado de cobro inválido")
        invoice.status = status
        invoice.paid_at = datetime.now(UTC) if invoice.status == "Pagada" else None
        session.commit()
        set_flash(request, f"Estado de {invoice.reference} actualizado.")
        return RedirectResponse("/administracion-saas", status_code=303)
