from __future__ import annotations

import json
import secrets
from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .commercial_lifecycle import LifecycleTransitionError, ensure_proposal_can_send
from .commercial_pricing import proposal_first_year_total, proposal_initial_payment, recurring_first_year_value
from .config import settings
from .database import get_db
from .db.models import CommercialLead, CommercialProposal, DiagnosticAssessment, PaymentTransaction, ServicePlan
from .monetary import parse_nonnegative_money, parse_nonnegative_rate


def _parse_nonnegative_number(value: object, field_name: str):
    """Compatibility name for V2.60.5 money inputs, now backed by exact money policy.

    The historical helper name is retained because downstream readiness checks
    and integrations identify this boundary by name. Its semantics are no
    longer generic numeric parsing: all callers in this module are monetary and
    therefore inherit V2.60.7–V2.60.9 rounding, finiteness and portable-range
    enforcement through ``parse_nonnegative_money``.
    """

    return parse_nonnegative_money(value, field_name)


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

    def _commercial_data(session: Session) -> dict[str, object]:
        leads = list(session.scalars(select(CommercialLead).order_by(CommercialLead.created_at.desc())))
        proposals = list(session.scalars(
            select(CommercialProposal)
            .options(selectinload(CommercialProposal.lead), selectinload(CommercialProposal.plan))
            .order_by(CommercialProposal.created_at.desc())
        ))
        payments = list(session.scalars(
            select(PaymentTransaction)
            .options(selectinload(PaymentTransaction.proposal))
            .order_by(PaymentTransaction.created_at.desc())
            .limit(50)
        ))
        plans = list(session.scalars(
            select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.id)
        ))

        assessment_by_lead: dict[int, DiagnosticAssessment] = {}
        lead_ids = [lead.id for lead in leads]
        if lead_ids:
            assessments = session.scalars(
                select(DiagnosticAssessment)
                .where(DiagnosticAssessment.lead_id.in_(lead_ids))
                .order_by(DiagnosticAssessment.assessed_at.desc(), DiagnosticAssessment.id.desc())
            )
            for assessment in assessments:
                if assessment.lead_id is not None and assessment.lead_id not in assessment_by_lead:
                    assessment_by_lead[assessment.lead_id] = assessment

        summary = {
            "leads": len(leads),
            "qualified": sum(1 for item in leads if item.status in {"Calificado", "Propuesta"}),
            "proposals": len(proposals),
            "accepted": sum(1 for item in proposals if item.status == "Aceptada"),
            "pipeline": round(sum(
                item.first_year_total
                for item in proposals
                if item.status in {"Borrador", "Enviada", "Vista", "Aceptada"}
            )),
            "paid": round(sum(item.amount for item in payments if item.status == "Pagada")),
        }
        return {
            "leads": leads,
            "proposals": proposals,
            "payments": payments,
            "plans": plans,
            "assessment_by_lead": assessment_by_lead,
            "summary": summary,
        }

    def _render_commercial(
        request: Request,
        session: Session,
        user,
        *,
        proposal_error: str = "",
        proposal_form_values: dict[str, object] | None = None,
        status_code: int = 200,
    ):
        data = _commercial_data(session)
        context = common_context(
            request,
            session,
            user,
            "commercial",
            **data,
            proposal_error=proposal_error,
            proposal_form_values=proposal_form_values or {},
            proposal_min_valid_until=date.today().isoformat(),
        )
        return templates.TemplateResponse(
            request,
            "commercial.html",
            context,
            status_code=status_code,
        )

    @app.get("/comercial", response_class=HTMLResponse)
    def commercial_center(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        return _render_commercial(request, session, user)

    @app.post("/comercial/leads/{lead_id}/estado")
    def update_commercial_lead(
        lead_id: int,
        request: Request,
        status: str = Form(...),
        assigned_to: str = Form("Equipo comercial"),
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
        request: Request,
        lead_id: int = Form(...),
        plan_id: int = Form(...),
        title: str = Form(""),
        implementation_fee: str = Form(""),
        recurring_fee: str = Form(""),
        discount_amount: str = Form("0"),
        tax_rate: str = Form(""),
        billing_cycle: str = Form(""),
        valid_until: str = Form(""),
        scope: str = Form(""),
        deliverables: str = Form(""),
        terms: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        lead = session.get(CommercialLead, lead_id)
        plan = session.get(ServicePlan, plan_id)
        if not lead or not plan:
            raise HTTPException(404, "Prospecto o plan no encontrado")

        form_values: dict[str, object] = {
            "lead_id": lead_id,
            "plan_id": plan_id,
            "title": title,
            "implementation_fee": implementation_fee,
            "recurring_fee": recurring_fee,
            "discount_amount": discount_amount,
            "tax_rate": tax_rate,
            "billing_cycle": billing_cycle,
            "valid_until": valid_until,
            "scope": scope,
            "deliverables": deliverables,
            "terms": terms,
        }

        try:
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Define el título de la propuesta.")
            if not plan.active:
                raise ValueError("El plan seleccionado ya no está activo. Selecciona otro plan.")

            implementation_value = _parse_nonnegative_number(implementation_fee, "el valor de implementación")
            recurring_value = _parse_nonnegative_number(recurring_fee, "el valor recurrente por ciclo")
            discount_value = _parse_nonnegative_number(discount_amount, "el descuento inicial")
            tax_value = parse_nonnegative_rate(tax_rate, "la tasa de impuesto")

            if billing_cycle not in {"Mensual", "Anual"}:
                raise ValueError("Selecciona un ciclo de facturación válido.")

            initial_subtotal_before_discount = implementation_value + recurring_value
            if discount_value > initial_subtotal_before_discount:
                raise ValueError(
                    "El descuento inicial no puede superar el primer cobro: implementación más un ciclo recurrente."
                )

            if not valid_until.strip():
                raise ValueError("Define hasta cuándo es válida la propuesta.")
            try:
                valid_until_date = date.fromisoformat(valid_until)
            except ValueError as exc:
                raise ValueError("La fecha de vigencia no es válida.") from exc
            if valid_until_date < date.today():
                raise ValueError("La fecha de vigencia no puede estar en el pasado.")

            scope_items = [item.strip() for item in scope.splitlines() if item.strip()]
            if not scope_items:
                raise ValueError("Define al menos un elemento de alcance.")
            deliverable_items = [item.strip() for item in deliverables.splitlines() if item.strip()]
            if not deliverable_items:
                raise ValueError("Define al menos un entregable.")
            clean_terms = terms.strip()
            if not clean_terms:
                raise ValueError("Define las condiciones de la propuesta.")
        except ValueError as exc:
            return _render_commercial(
                request,
                session,
                user,
                proposal_error=str(exc),
                proposal_form_values=form_values,
                status_code=400,
            )

        today = date.today()
        sequence = (session.scalar(select(func.count(CommercialProposal.id))) or 0) + 1
        reference = f"PROP-{today.year}-{sequence:04d}"
        while session.scalar(select(CommercialProposal).where(CommercialProposal.reference == reference)):
            sequence += 1
            reference = f"PROP-{today.year}-{sequence:04d}"

        proposal = CommercialProposal(
            lead_id=lead.id,
            plan_id=plan.id,
            reference=reference,
            public_token=secrets.token_urlsafe(24),
            title=clean_title,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            contact_email=lead.email,
            status="Borrador",
            valid_until=valid_until_date,
            billing_cycle=billing_cycle,
            implementation_fee=implementation_value,
            recurring_fee=recurring_value,
            discount_amount=discount_value,
            tax_rate=tax_value,
            first_year_total=proposal_first_year_total(
                implementation_value,
                recurring_value,
                discount_value,
                tax_value,
                billing_cycle,
            ),
            scope_json=json.dumps(scope_items, ensure_ascii=False),
            deliverables_json=json.dumps(deliverable_items, ensure_ascii=False),
            terms=clean_terms,
            contract_version="1.1",
            created_by=str(user["email"]),
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
        try:
            ensure_proposal_can_send(proposal)
        except LifecycleTransitionError as exc:
            raise HTTPException(409, str(exc)) from exc
        proposal.status = "Enviada"
        proposal.sent_at = datetime.now(UTC)
        session.commit()
        set_flash(request, f"Propuesta {proposal.reference} marcada como enviada. Enlace público disponible.")
        return RedirectResponse("/comercial", status_code=303)

    @app.get("/propuesta/{token}", response_class=HTMLResponse)
    def public_proposal(token: str, request: Request, session: Session = Depends(get_db)):
        proposal = session.scalar(
            select(CommercialProposal)
            .where(CommercialProposal.public_token == token)
            .options(selectinload(CommercialProposal.plan))
        )
        if not proposal:
            raise HTTPException(404, "Propuesta no encontrada")
        if proposal.status == "Enviada":
            proposal.status = "Vista"
        if not proposal.viewed_at:
            proposal.viewed_at = datetime.now(UTC)
        session.commit()
        payment = session.scalar(
            select(PaymentTransaction)
            .where(PaymentTransaction.proposal_id == proposal.id)
            .order_by(PaymentTransaction.id.desc())
            .limit(1)
        )
        return templates.TemplateResponse(
            request=request,
            name="public_proposal.html",
            context={
                "proposal": proposal,
                "scope_items": _proposal_items(proposal.scope_json),
                "deliverables": _proposal_items(proposal.deliverables_json),
                "payment": payment,
                "initial_payment": proposal_initial_payment(
                    proposal.implementation_fee,
                    proposal.recurring_fee,
                    proposal.discount_amount,
                    proposal.tax_rate,
                ),
                "recurring_first_year": recurring_first_year_value(
                    proposal.recurring_fee,
                    proposal.billing_cycle,
                ),
                "app_settings": settings,
            },
        )