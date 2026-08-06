from __future__ import annotations

import json

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from .database import get_db
from .delivery_readiness import professional_delivery_summary
from .repositories.reports import list_report_artifacts


def register_delivery_routes(app, templates, common_context, require_user, get_inventory) -> None:
    @app.get("/entrega-profesional", response_class=HTMLResponse)
    def professional_delivery(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user)
        delivery = professional_delivery_summary(session, inventory)
        artifacts = list_report_artifacts(session, inventory.id)
        return templates.TemplateResponse(
            request=request,
            name="delivery.html",
            context=common_context(
                request,
                session,
                user,
                "delivery",
                inventory=inventory,
                delivery=delivery,
                artifacts=artifacts,
                **delivery["analysis"],
            ),
        )

    @app.get("/api/entrega-profesional/resumen")
    def professional_delivery_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user)
        delivery = professional_delivery_summary(session, inventory)
        payload = {
            "inventory_id": inventory.id,
            "inventory": inventory.name,
            "version": inventory.version,
            "status": delivery["status"],
            "score": delivery["score"],
            "release_ready": delivery["release_ready"],
            "approved": delivery["approved"],
            "publication": delivery["publication"],
            "decision": delivery["decision"],
            "action_plan": delivery["action_plan"],
            "metrics": delivery["metrics"],
            "gates": [
                {key: gate[key] for key in ("code", "name", "status", "detail", "href")}
                for gate in delivery["gates"]
            ],
            "blockers": [item["name"] for item in delivery["blockers"]],
            "next_action": delivery["next_action"],
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=False, default=str),
            media_type="application/json",
        )
