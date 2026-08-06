from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import get_db
from .service_operations import operation_summary


def register_service_operations_routes(app, templates, common_context, require_user, ensure_capability) -> None:
    @app.get("/operacion-servicio", response_class=HTMLResponse)
    def service_operations_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_subscription")
        summary = operation_summary(session, int(user["organization_id"]))
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="service_operations.html",
            context=common_context(request, session, user, "service_operations", summary=summary),
        )

    @app.get("/api/operacion-servicio/resumen")
    def service_operations_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_subscription")
        summary = operation_summary(session, int(user["organization_id"]))
        subscription = summary["subscription"]
        plan = summary["plan"]
        session.commit()
        return {
            "subscription": {
                "status": subscription.status if subscription else "Sin plan",
                "plan": plan.name if plan else None,
                "renewal_date": subscription.renewal_date.isoformat() if subscription and subscription.renewal_date else None,
            },
            "capacity": summary["metrics"],
            "pending_invitations": len(summary["pending_invitations"]),
            "open_tickets": summary["open_tickets"],
            "overdue_invoices": len(summary["overdue_invoices"]),
            "actions": summary["actions"],
        }
