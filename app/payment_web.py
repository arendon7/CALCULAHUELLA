from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import Depends, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .commercial_pricing import proposal_initial_payment, subscription_custom_monthly_fee
from .config import settings
from .database import get_db
from .db.models import (
    BillingInvoice,
    CommercialLead,
    CommercialProposal,
    CustomerOnboardingItem,
    Organization,
    OrganizationSubscription,
    PaymentTransaction,
)
from .monetary import MONEY_QUANTUM, RATE_QUANTUM, quantize_money, quantize_rate
from .revenue_operations import INVOICE_TOTAL_WITH_TAX, activation_breakdown


class PaymentWebhookPayload(BaseModel):
    external_reference: str = Field(min_length=3, max_length=120)
    status: str = Field(min_length=3, max_length=30)
    amount: Decimal = Field(ge=0)
    payer_email: str = ""


def _next_billing_date(start: date, billing_cycle: str) -> date:
    safe_day = min(start.day, 28)
    if billing_cycle == "Mensual":
        if start.month == 12:
            return date(start.year + 1, 1, safe_day)
        return date(start.year, start.month + 1, safe_day)
    return date(start.year + 1, start.month, safe_day)


def _ensure_supported_billing_contract(proposal: CommercialProposal) -> None:
    if proposal.billing_cycle == "Mensual" and proposal.contract_version != "1.1":
        raise HTTPException(
            409,
            "La propuesta mensual usa una versión contractual anterior. Debe regenerarse antes de aceptar o confirmar pagos.",
        )


def _canonical_acceptance_timestamp(value: datetime) -> str:
    """Normalize ORM round-trips so an acceptance snapshot can be recomputed byte-for-byte."""
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return normalized.isoformat()


def _proposal_acceptance_source(
    proposal: CommercialProposal,
    accepted_by: str,
    accepted_email: str,
    accepted_at: datetime,
) -> str:
    """Canonical acceptance snapshot binding identity, scope and complete economics."""
    payload = {
        "reference": proposal.reference,
        "contract_version": proposal.contract_version,
        "billing_cycle": proposal.billing_cycle,
        "implementation_fee": f"{quantize_money(proposal.implementation_fee):.2f}",
        "recurring_fee": f"{quantize_money(proposal.recurring_fee):.2f}",
        "discount_amount": f"{quantize_money(proposal.discount_amount):.2f}",
        "tax_rate": f"{quantize_rate(proposal.tax_rate):.4f}",
        "first_year_total": f"{quantize_money(proposal.first_year_total):.2f}",
        "scope_json": proposal.scope_json,
        "deliverables_json": proposal.deliverables_json,
        "terms": proposal.terms,
        "accepted_by": accepted_by.strip(),
        "accepted_email": accepted_email.strip().lower(),
        "accepted_at": _canonical_acceptance_timestamp(accepted_at),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _classify_activation_invoice(
    invoice: BillingInvoice,
    proposal: CommercialProposal,
    payment: PaymentTransaction,
) -> None:
    parts = activation_breakdown(
        proposal.implementation_fee,
        proposal.recurring_fee,
        proposal.discount_amount,
        proposal.tax_rate,
    )
    payment_amount = quantize_money(payment.amount)
    invoice_amount = quantize_money(invoice.amount)
    if abs(parts["total_amount"] - payment_amount) > MONEY_QUANTUM:
        raise HTTPException(409, "El pago de activación no coincide con el snapshot económico aceptado")
    if abs(invoice_amount - payment_amount) > MONEY_QUANTUM:
        raise HTTPException(409, "El cobro existente no coincide con el pago de activación aceptado")

    if invoice.amount_semantics is not None:
        expected = {
            "charge_type": "Activación",
            "amount_semantics": INVOICE_TOTAL_WITH_TAX,
            "net_amount": parts["net_amount"],
            "tax_rate_snapshot": parts["tax_rate_snapshot"],
            "tax_amount": parts["tax_amount"],
            "total_amount": parts["total_amount"],
            "source_reference": proposal.reference,
        }
        actual = {
            "charge_type": invoice.charge_type,
            "amount_semantics": invoice.amount_semantics,
            "net_amount": invoice.net_amount,
            "tax_rate_snapshot": invoice.tax_rate_snapshot,
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "source_reference": invoice.source_reference,
        }
        money_keys = {"net_amount", "tax_amount", "total_amount"}
        for key, expected_value in expected.items():
            actual_value = actual[key]
            if key in money_keys:
                if actual_value is None or abs(quantize_money(actual_value) - expected_value) > MONEY_QUANTUM:
                    raise HTTPException(409, "La clasificación económica existente no coincide con la propuesta aceptada")
            elif key == "tax_rate_snapshot":
                if actual_value is None or abs(quantize_rate(actual_value) - expected_value) > RATE_QUANTUM:
                    raise HTTPException(409, "La clasificación económica existente no coincide con la propuesta aceptada")
            elif actual_value != expected_value:
                raise HTTPException(409, "La clasificación económica existente no coincide con la propuesta aceptada")
        return

    invoice.charge_type = "Activación"
    invoice.amount_semantics = INVOICE_TOTAL_WITH_TAX
    invoice.net_amount = parts["net_amount"]
    invoice.tax_rate_snapshot = parts["tax_rate_snapshot"]
    invoice.tax_amount = parts["tax_amount"]
    invoice.total_amount = parts["total_amount"]
    invoice.source_reference = proposal.reference
    invoice.classification_note = (
        "Total de activación derivado de la propuesta aceptada: implementación + primer ciclo - descuento inicial + impuesto."
    )
    invoice.semantics_created_at = payment.paid_at or datetime.now(UTC)


def register_payment_routes(app, templates) -> None:
    @app.post("/propuesta/{token}/aceptar")
    def accept_public_proposal(
        token: str, request: Request, accepted_by: str = Form(...), accepted_email: str = Form(...),
        accept_terms: str | None = Form(None), session: Session = Depends(get_db),
    ):
        proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.public_token == token))
        if not proposal:
            raise HTTPException(404, "Propuesta no encontrada")
        if not accept_terms:
            raise HTTPException(400, "Debes aceptar las condiciones de la propuesta")
        if proposal.valid_until and proposal.valid_until < date.today():
            proposal.status = "Vencida"
            session.commit()
            raise HTTPException(409, "La propuesta está vencida")
        _ensure_supported_billing_contract(proposal)
        timestamp = datetime.now(UTC)
        client_ip = request.client.host if request.client else "unknown"
        acceptance_source = _proposal_acceptance_source(proposal, accepted_by, accepted_email, timestamp)
        proposal.status = "Aceptada"
        proposal.accepted_by = accepted_by.strip()
        proposal.accepted_email = accepted_email.strip().lower()
        proposal.accepted_ip = client_ip
        proposal.accepted_at = timestamp
        proposal.acceptance_hash = hashlib.sha256(acceptance_source.encode("utf-8")).hexdigest()
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal.id).order_by(PaymentTransaction.id.desc()).limit(1))
        if not payment:
            payment = PaymentTransaction(
                proposal_id=proposal.id, public_token=secrets.token_urlsafe(24), gateway="Demo",
                status="Pendiente",
                amount=proposal_initial_payment(
                    proposal.implementation_fee,
                    proposal.recurring_fee,
                    proposal.discount_amount,
                    proposal.tax_rate,
                ),
                currency="COP",
                external_reference=f"PAY-{proposal.reference}", payer_name=proposal.accepted_by,
                payer_email=proposal.accepted_email, provider_payload='{"mode": "demo", "charge": "activation"}',
            )
            session.add(payment)
        session.commit()
        return RedirectResponse(f"/pago/{payment.public_token}", status_code=303)

    @app.post("/propuesta/{token}/rechazar")
    def reject_public_proposal(token: str, request: Request, reason: str = Form(""), session: Session = Depends(get_db)):
        proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.public_token == token))
        if not proposal:
            raise HTTPException(404, "Propuesta no encontrada")
        proposal.status = "Rechazada"
        proposal.rejection_reason = reason.strip()
        session.commit()
        return RedirectResponse(f"/propuesta/{token}", status_code=303)

    @app.get("/pago/{token}", response_class=HTMLResponse)
    def public_payment(token: str, request: Request, session: Session = Depends(get_db)):
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.public_token == token).options(selectinload(PaymentTransaction.proposal)))
        if not payment:
            raise HTTPException(404, "Pago no encontrado")
        return templates.TemplateResponse(request=request, name="public_payment.html", context={"payment": payment, "proposal": payment.proposal, "app_settings": settings})

    @app.post("/pago/{token}/confirmar")
    def confirm_demo_payment(
        token: str, request: Request, payer_name: str = Form(...), payer_email: str = Form(...),
        method: str = Form("Transferencia demostrativa"), session: Session = Depends(get_db),
    ):
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.public_token == token).options(selectinload(PaymentTransaction.proposal)))
        if not payment or not payment.proposal:
            raise HTTPException(404, "Pago no encontrado")
        proposal = payment.proposal
        if proposal.status != "Aceptada":
            raise HTTPException(409, "La propuesta debe aceptarse antes del pago")
        _ensure_supported_billing_contract(proposal)
        payment.status = "Pagada"
        payment.gateway = "Demo"
        payment.payer_name = payer_name.strip()
        payment.payer_email = payer_email.strip().lower()
        payment.paid_at = datetime.now(UTC)
        payment.provider_payload = json.dumps({"mode": "demo", "method": method, "charge": "activation", "confirmed_at": payment.paid_at.isoformat()}, ensure_ascii=False)
        if not proposal.organization_id:
            base_name = proposal.company_name.strip()
            organization = session.scalar(select(Organization).where(Organization.name == base_name))
            if not organization:
                lead = session.get(CommercialLead, proposal.lead_id) if proposal.lead_id else None
                organization = Organization(
                    name=base_name, trade_name=base_name, tax_id="PENDIENTE", sector=lead.sector if lead else "Por configurar",
                    country="Colombia", city=lead.city if lead else "Por configurar", employees=0,
                    contact_name=proposal.contact_name, contact_email=proposal.contact_email, status="Activa",
                )
                session.add(organization)
                session.flush()
            proposal.organization_id = organization.id
            subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization.id))
            if not subscription and proposal.plan_id:
                renewal = date(date.today().year + 1, date.today().month, min(date.today().day, 28))
                subscription = OrganizationSubscription(
                    organization_id=organization.id, plan_id=proposal.plan_id, billing_cycle=proposal.billing_cycle,
                    status="Activa", start_date=date.today(), renewal_date=renewal,
                    custom_monthly_fee=subscription_custom_monthly_fee(
                        proposal.recurring_fee,
                        proposal.billing_cycle,
                    ),
                    notes=(
                        f"Activada desde propuesta {proposal.reference}; conserva el valor base recurrente negociado "
                        f"por ciclo. Impuesto contractual de {proposal.tax_rate:g}% se conserva en la propuesta y se "
                        "liquida en el documento tributario/pago final, no dentro de custom_monthly_fee."
                    ),
                )
                session.add(subscription)
                session.flush()
            invoice = session.scalar(select(BillingInvoice).where(BillingInvoice.reference == f"COBRO-{proposal.reference}"))
            if not invoice:
                invoice = BillingInvoice(
                    organization_id=organization.id, subscription_id=subscription.id if subscription else None,
                    reference=f"COBRO-{proposal.reference}", period_start=date.today(),
                    period_end=_next_billing_date(date.today(), proposal.billing_cycle),
                    amount=payment.amount, status="Pagada", issued_at=date.today(), due_date=date.today(),
                    paid_at=payment.paid_at,
                    notes="Cobro de activación generado desde el pago demostrativo. Incluye implementación, primer ciclo recurrente, descuento inicial e impuestos según la propuesta. No constituye factura electrónica.",
                )
                session.add(invoice)
                session.flush()
            _classify_activation_invoice(invoice, proposal, payment)
            payment.subscription_id = subscription.id if subscription else None
            payment.invoice_id = invoice.id
            onboarding_specs = [
                ("ORG-01", "Organización", "Completar información legal y operativa", 10),
                ("USR-01", "Accesos", "Invitar responsables y definir roles", 20),
                ("MET-01", "Metodología", "Aprobar metodología y límites", 30),
                ("DAT-01", "Información", "Cargar el primer conjunto de datos", 40),
                ("CAL-01", "Cálculo", "Validar el primer cálculo trazable", 50),
                ("REP-01", "Entrega", "Generar el primer informe", 60),
            ]
            for code, category, title, order in onboarding_specs:
                if not session.scalar(select(CustomerOnboardingItem).where(CustomerOnboardingItem.organization_id == organization.id, CustomerOnboardingItem.code == code)):
                    session.add(CustomerOnboardingItem(
                        organization_id=organization.id, code=code, category=category, title=title,
                        description="Actividad creada automáticamente después de la contratación.", status="Pendiente",
                        owner="Cliente", display_order=order, updated_by="sistema",
                    ))
        if proposal.lead_id:
            lead = session.get(CommercialLead, proposal.lead_id)
            if lead:
                lead.status = "Ganado"
        session.commit()
        return RedirectResponse(f"/pago/{token}", status_code=303)

    @app.post("/api/pagos/webhook")
    def payment_webhook(payload: PaymentWebhookPayload, x_payment_secret: str | None = Header(None), session: Session = Depends(get_db)):
        if not settings.payment_webhook_secret or not hmac.compare_digest(x_payment_secret or "", settings.payment_webhook_secret):
            raise HTTPException(401, "Firma de pago inválida")
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.external_reference == payload.external_reference).options(selectinload(PaymentTransaction.proposal)))
        if not payment:
            raise HTTPException(404, "Transacción no encontrada")
        if payment.proposal:
            _ensure_supported_billing_contract(payment.proposal)
        if abs(quantize_money(payment.amount) - quantize_money(payload.amount)) > MONEY_QUANTUM:
            raise HTTPException(409, "El valor informado no coincide")
        normalized_status = payload.status.strip().lower()
        mapping = {"paid": "Pagada", "approved": "Pagada", "pending": "Pendiente", "failed": "Fallida", "declined": "Fallida", "refunded": "Reembolsada"}
        payment.status = mapping.get(normalized_status, payload.status[:30])
        payment.payer_email = payload.payer_email.strip().lower() or payment.payer_email
        payment.paid_at = datetime.now(UTC) if payment.status == "Pagada" else payment.paid_at
        payment.provider_payload = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
        session.commit()
        return {"ok": True, "transaction_id": payment.id, "status": payment.status}
