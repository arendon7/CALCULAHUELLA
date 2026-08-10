from __future__ import annotations

from datetime import date

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import (
    BillingInvoice, EvidenceDocument, Facility, Inventory, OrganizationMembership,
    OrganizationSubscription, ServicePlan, UsageCounter,
)


def _service_usage(session: Session, organization_id: int, plan: ServicePlan | None) -> dict[str, object]:
    users = session.scalar(select(func.count(OrganizationMembership.id)).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
    )) or 0
    facilities = session.scalar(select(func.count(Facility.id)).where(Facility.organization_id == organization_id)) or 0
    inventories = session.scalar(select(func.count(Inventory.id)).where(Inventory.organization_id == organization_id)) or 0
    storage_bytes = session.scalar(
        select(func.coalesce(func.sum(EvidenceDocument.file_size), 0))
        .join(Inventory, EvidenceDocument.inventory_id == Inventory.id)
        .where(Inventory.organization_id == organization_id)
    ) or 0
    storage_mb = round(float(storage_bytes) / (1024 * 1024), 2)
    values = {
        "users": {"value": int(users), "limit": plan.max_users if plan else 0, "label": "Usuarios"},
        "facilities": {"value": int(facilities), "limit": plan.max_facilities if plan else 0, "label": "Sedes"},
        "inventories": {"value": int(inventories), "limit": plan.max_inventories if plan else 0, "label": "Inventarios"},
        "storage": {"value": storage_mb, "limit": plan.max_storage_mb if plan else 0, "label": "Almacenamiento MB"},
    }
    period = date.today().replace(day=1)
    metric_map = {"users": users, "facilities": facilities, "inventories": inventories, "storage_mb": storage_mb}
    for metric, value in metric_map.items():
        counter = session.scalar(select(UsageCounter).where(
            UsageCounter.organization_id == organization_id,
            UsageCounter.metric == metric,
            UsageCounter.period_start == period,
        ))
        if counter:
            counter.value = float(value)
        else:
            session.add(UsageCounter(organization_id=organization_id, metric=metric, period_start=period, value=float(value)))
    for item in values.values():
        limit = float(item["limit"] or 0)
        item["percentage"] = min(100, round(float(item["value"]) / limit * 100)) if limit else 0
        item["exceeded"] = bool(limit and float(item["value"]) > limit)
    return values


def register_service_account_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/cuenta-servicio", response_class=HTMLResponse)
    def service_account(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        subscription = session.scalar(
            select(OrganizationSubscription)
            .where(OrganizationSubscription.organization_id == int(user["organization_id"]))
            .options(selectinload(OrganizationSubscription.plan))
        )
        plans = list(session.scalars(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.monthly_fee)))
        usage = _service_usage(session, int(user["organization_id"]), subscription.plan if subscription else None)
        invoices = list(session.scalars(select(BillingInvoice).where(BillingInvoice.organization_id == int(user["organization_id"])).order_by(BillingInvoice.issued_at.desc())))
        session.commit()
        return templates.TemplateResponse(request, "service_account.html", common_context(
            request, session, user, "service_account", subscription=subscription, plans=plans, usage=usage, invoices=invoices,
        ))

    @app.post("/cuenta-servicio/suscripcion")
    def update_subscription(
        request: Request,
        plan_id: int = Form(...),
        billing_cycle: str = Form("Anual"),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_subscription")
        plan = session.get(ServicePlan, plan_id)
        if not plan or not plan.active:
            raise HTTPException(404, "Plan no disponible")
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == int(user["organization_id"])))
        previous = subscription.plan_id if subscription else None
        if subscription:
            subscription.plan_id = plan.id
            subscription.billing_cycle = billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual"
            subscription.status = "Activa"
            subscription.start_date = date.today()
        else:
            subscription = OrganizationSubscription(
                organization_id=int(user["organization_id"]), plan_id=plan.id,
                billing_cycle=billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual",
                status="Activa", start_date=date.today(),
            )
            session.add(subscription)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Suscripción", plan.name, previous_value=str(previous or ""), new_value=str(plan.id))
        session.commit()
        set_flash(request, f"Plan actualizado a {plan.name}. Esta operación es administrativa y no procesa pagos.")
        return RedirectResponse("/cuenta-servicio", status_code=303)
