from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .db.models import (
    ComplianceAssessment, DocumentControlRecord, EmissionSource, Inventory,
    OrganizationMembership, ReductionAction, ReviewObservation,
)


def register_executive_portfolio_routes(
    app, templates, common_context, require_user, ensure_capability, _compliance_score
) -> None:
    @app.get("/direccion-ejecutiva", response_class=HTMLResponse)
    def executive_portfolio_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_portfolio")
        memberships = list(session.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == int(user["id"]), OrganizationMembership.active.is_(True))
            .options(selectinload(OrganizationMembership.organization))
            .order_by(OrganizationMembership.id)
        ))
        cards = []
        portfolio_total = 0.0
        total_reduction = 0.0
        for membership in memberships:
            organization = membership.organization
            inventory = session.scalar(select(Inventory).where(Inventory.organization_id == organization.id).order_by(Inventory.start_date.desc(), Inventory.id.desc()).limit(1))
            if inventory:
                emissions = session.scalar(select(func.coalesce(func.sum(EmissionSource.emissions), 0.0)).where(EmissionSource.inventory_id == inventory.id, EmissionSource.included.is_(True))) or 0.0
                assessments = list(session.scalars(select(ComplianceAssessment).where(ComplianceAssessment.inventory_id == inventory.id).options(selectinload(ComplianceAssessment.requirement))))
                open_observations = session.scalar(select(func.count(ReviewObservation.id)).where(ReviewObservation.inventory_id == inventory.id, ReviewObservation.status != "Cerrada")) or 0
                reduction = session.scalar(select(func.coalesce(func.sum(ReductionAction.expected_reduction), 0.0)).where(ReductionAction.inventory_id == inventory.id)) or 0.0
                documents = session.scalar(select(func.count(DocumentControlRecord.id)).where(DocumentControlRecord.organization_id == organization.id)) or 0
                portfolio_total += float(emissions)
                total_reduction += float(reduction)
                cards.append({"organization": organization, "membership": membership, "inventory": inventory, "emissions": float(emissions), "compliance": _compliance_score(assessments), "open_observations": open_observations, "reduction": float(reduction), "documents": documents})
            else:
                cards.append({"organization": organization, "membership": membership, "inventory": None, "emissions": 0.0, "compliance": 0, "open_observations": 0, "reduction": 0.0, "documents": 0})
        average_compliance = round(sum(item["compliance"] for item in cards) / max(len(cards), 1))
        return templates.TemplateResponse(request=request, name="executive_portfolio.html", context=common_context(request, session, user, "executive", cards=cards, portfolio_total=portfolio_total, total_reduction=total_reduction, average_compliance=average_compliance))
