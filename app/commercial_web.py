from __future__ import annotations

import json
import secrets
from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import get_db
from .db.models import CommercialLead, CommercialProposal, PaymentTransaction, ServicePlan


def register_commercial_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
) -> None:
    def _proposal_items(raw: str) -> list[str]:
        try:
            parsed = json.loads(raw or "[]")
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _proposal_total(implementation_fee: float, recurring_fee: float, discount_amount: float, tax_rate: float) -> float:
        subtotal = max(0.0, implementation_fee) + max(0.0, recurring_fee) - max(0.0, discount_amount)
        return round(max(0.0, subtotal) * (1 + max(0.0, tax_rate) / 100), 2)

    @app.get("/comercial", response_class=HTMLResponse)
    def commercial_center(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        leads = list(session.scalars(select(CommercialLead).order_by(CommercialLead.created_at.desc())))
        proposals = list(session.scalars(
            select(CommercialProposal).options(selectinload(CommercialProposal.lead), selectinload(CommercialProposal.plan)).order_by(CommercialProposal.created_at.desc())
        ))
        payments = list(session.scalars(
            select(PaymentTransaction).options(selectinload(PaymentTransaction.proposal)).order_by(PaymentTransaction.created_at.desc()).limit(50)
        ))
        plans = list(session.scalars(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.monthly_fee)))
        summary = {
            "leads": len(leads), "qualified": sum(1 for item in leads if item.status in {"Calificado", "Propuesta"}),
            "proposals": len(proposals), "accepted": sum(1 for item in proposals if item.status == "Aceptada"),
            "pipeline": round(sum(item.first_year_total for item in proposals if item.status in {"Borrador", "Enviada", "Vista", "Aceptada"})),
            "paid": round(sum(item.amount for item in payments if item.status == "Pagada")),
        }
        return templates.TemplateResponse(request, "commercial.html", common_context(
            request, session, user, "commercial", leads=leads, proposals=proposals, payments=payments, plans=plans, summary=summary,
        ))

    @app.post("/comercial/leads/{lead_id}/estado")
    def update_commercial_lead(
        lead_id: int, request: Request, status: str = Form(...), assigned_to: str = Form("Equipo comercial"),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        lead = session.get(CommercialLead, lead_id)
        if not lead:
            raise HTTPException(404, "Prospecto no encontrado")
        valid = {"Nuevo", "Contactado", "Calificado", "Propuesta", "Ganado", "Descartado"}
        lead.status = status if status in valid else lead.status
        lead.assigned_to = assigned_to.strip() or lead.assigned_to
        session.commit()
        set_flash(request, f"Prospecto {lead.company_name} actualizado.")
        return RedirectResponse("/comercial", status_code=303)

    @app.post("/comercial/propuestas/nueva")
    def create_commercial_proposal(
        request: Request, lead_id: int = Form(...), plan_id: int = Form(...), title: str = Form(...),
        implementation_fee: float = Form(0), recurring_fee: float = Form(0), discount_amount: float = Form(0),
        tax_rate: float = Form(19), billing_cycle: str = Form("Anual"), valid_until: str = Form(""),
        scope: str = Form(""), deliverables: str = Form(""), terms: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        lead = session.get(CommercialLead, lead_id)
        plan = session.get(ServicePlan, plan_id)
        if not lead or not plan:
            raise HTTPException(404, "Prospecto o plan no encontrado")
        today = date.today()
        sequence = (session.scalar(select(func.count(CommercialProposal.id))) or 0) + 1
        reference = f"PROP-{today.year}-{sequence:04d}"
        while session.scalar(select(CommercialProposal).where(CommercialProposal.reference == reference)):
            sequence += 1
            reference = f"PROP-{today.year}-{sequence:04d}"
        proposal = CommercialProposal(
            lead_id=lead.id, plan_id=plan.id, reference=reference, public_token=secrets.token_urlsafe(24),
            title=title.strip(), company_name=lead.company_name, contact_name=lead.contact_name, contact_email=lead.email,
            status="Borrador", valid_until=parse_date(valid_until) if valid_until else None,
            billing_cycle=billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual",
            implementation_fee=max(0, implementation_fee), recurring_fee=max(0, recurring_fee),
            discount_amount=max(0, discount_amount), tax_rate=max(0, tax_rate),
            first_year_total=_proposal_total(implementation_fee, recurring_fee, discount_amount, tax_rate),
            scope_json=json.dumps([item.strip() for item in scope.splitlines() if item.strip()], ensure_ascii=False),
            deliverables_json=json.dumps([item.strip() for item in deliverables.splitlines() if item.strip()], ensure_ascii=False),
            terms=terms.strip(), contract_version="1.0", created_by=str(user["email"]),
        )
        session.add(proposal)
        lead.status = "Propuesta"
        session.commit()
        set_flash(request, f"Propuesta {proposal.reference} creada.")
        return RedirectResponse("/comercial", status_code=303)

    @app.post("/comercial/propuestas/{proposal_id}/enviar")
    def send_commercial_proposal(proposal_id: int, request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        proposal = session.get(CommercialProposal, proposal_id)
        if not proposal:
            raise HTTPException(404, "Propuesta no encontrada")
        proposal.status = "Enviada"
        proposal.sent_at = datetime.now(UTC)
        session.commit()
        set_flash(request, f"Propuesta {proposal.reference} marcada como enviada. Enlace público disponible.")
        return RedirectResponse("/comercial", status_code=303)

    @app.get("/propuesta/{token}", response_class=HTMLResponse)
    def public_proposal(token: str, request: Request, session: Session = Depends(get_db)):
        proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.public_token == token).options(selectinload(CommercialProposal.plan)))
        if not proposal:
            raise HTTPException(404, "Propuesta no encontrada")
        if proposal.status == "Enviada":
            proposal.status = "Vista"
        if not proposal.viewed_at:
            proposal.viewed_at = datetime.now(UTC)
        session.commit()
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal.id).order_by(PaymentTransaction.id.desc()).limit(1))
        return templates.TemplateResponse(request=request, name="public_proposal.html", context={
            "proposal": proposal, "scope_items": _proposal_items(proposal.scope_json),
            "deliverables": _proposal_items(proposal.deliverables_json), "payment": payment, "app_settings": settings,
        })
