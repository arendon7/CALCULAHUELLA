from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import (
    BillingDocumentRecord,
    BillingInvoice,
    CollectionAction,
    CommercialProposal,
    Organization,
    OrganizationSubscription,
    ServiceContract,
    ServiceOrder,
)


def _contract_signature_hash(contract: ServiceContract, signed_by: str, signed_email: str, signed_at: datetime) -> str:
    payload = "|".join([
        contract.reference, str(contract.organization_id), contract.version,
        contract.start_date.isoformat(), contract.end_date.isoformat() if contract.end_date else "",
        f"{contract.contract_value:.2f}", contract.billing_cycle, contract.terms_snapshot,
        signed_by.strip(), signed_email.strip().lower(), signed_at.isoformat(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _contract_reference(session: Session) -> str:
    year = date.today().year
    current = session.scalar(select(func.count()).select_from(ServiceContract)) or 0
    return f"CTR-{year}-{int(current) + 1:04d}"

def _order_reference(session: Session) -> str:
    year = date.today().year
    current = session.scalar(select(func.count()).select_from(ServiceOrder)) or 0
    return f"OS-{year}-{int(current) + 1:04d}"


def register_commercial_operations_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, format_number
) -> None:
    @app.get("/operacion-comercial", response_class=HTMLResponse)
    def commercial_operations(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        contracts = list(session.scalars(
            select(ServiceContract)
            .options(selectinload(ServiceContract.organization), selectinload(ServiceContract.proposal))
            .order_by(ServiceContract.created_at.desc())
        ))
        orders = list(session.scalars(
            select(ServiceOrder)
            .options(selectinload(ServiceOrder.organization), selectinload(ServiceOrder.contract))
            .order_by(ServiceOrder.created_at.desc())
        ))
        invoices = list(session.scalars(select(BillingInvoice).order_by(BillingInvoice.issued_at.desc(), BillingInvoice.id.desc())))
        actions = list(session.scalars(
            select(CollectionAction)
            .options(selectinload(CollectionAction.organization), selectinload(CollectionAction.invoice))
            .order_by(CollectionAction.created_at.desc())
        ))
        documents = list(session.scalars(
            select(BillingDocumentRecord)
            .options(selectinload(BillingDocumentRecord.organization), selectinload(BillingDocumentRecord.invoice))
            .order_by(BillingDocumentRecord.created_at.desc())
        ))
        subscriptions = list(session.scalars(
            select(OrganizationSubscription)
            .options(selectinload(OrganizationSubscription.organization), selectinload(OrganizationSubscription.plan))
            .order_by(OrganizationSubscription.id)
        ))
        organizations = list(session.scalars(select(Organization).order_by(Organization.name)))
        org_map = {item.id: item for item in organizations}
        proposals = list(session.scalars(
            select(CommercialProposal)
            .where(CommercialProposal.status == "Aceptada", CommercialProposal.organization_id.is_not(None))
            .options(selectinload(CommercialProposal.organization), selectinload(CommercialProposal.plan))
            .order_by(CommercialProposal.accepted_at.desc())
        ))
        today = date.today()
        overdue = [item for item in invoices if item.status in {"Pendiente", "Vencida"} and item.due_date and item.due_date < today]
        outstanding = [item for item in invoices if item.status in {"Pendiente", "Vencida"}]
        renewals = [item for item in contracts if item.status == "Vigente" and item.end_date and 0 <= (item.end_date - today).days <= 120]
        summary = {
            "active_contracts": sum(1 for item in contracts if item.status == "Vigente"),
            "open_orders": sum(1 for item in orders if item.status not in {"Aceptada", "Cancelada"}),
            "outstanding_amount": round(sum(item.amount for item in outstanding), 2),
            "overdue_amount": round(sum(item.amount for item in overdue), 2),
            "renewals": len(renewals),
        }
        return templates.TemplateResponse(request, "commercial_operations.html", common_context(
            request, session, user, "commercial_operations",
            contracts=contracts, orders=orders, invoices=invoices, actions=actions, documents=documents,
            subscriptions=subscriptions, organizations=organizations, org_map=org_map, proposals=proposals,
            overdue=overdue, renewals=renewals, summary=summary, today=today,
        ))

    @app.post("/operacion-comercial/contratos/nuevo")
    def create_service_contract(
        request: Request,
        organization_id: int = Form(...), proposal_id: str = Form(""), reference: str = Form(""),
        title: str = Form(...), start_date: str = Form(...), end_date: str = Form(""),
        renewal_type: str = Form("Anual"), auto_renew: str | None = Form(None), notice_days: int = Form(30),
        contract_value: float = Form(0), billing_cycle: str = Form("Anual"), owner: str = Form("Equipo comercial"),
        terms_snapshot: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")
        proposal = session.get(CommercialProposal, int(proposal_id)) if proposal_id.strip().isdigit() else None
        normalized_reference = reference.strip().upper() or _contract_reference(session)
        if session.scalar(select(ServiceContract).where(ServiceContract.reference == normalized_reference)):
            raise HTTPException(409, "La referencia contractual ya existe")
        contract = ServiceContract(
            organization_id=organization.id, proposal_id=proposal.id if proposal else None,
            reference=normalized_reference, title=title.strip(), version="1.0", status="Borrador",
            start_date=parse_date(start_date), end_date=parse_date(end_date) if end_date else None,
            renewal_type=renewal_type.strip() or "Anual", auto_renew=bool(auto_renew), notice_days=max(0, notice_days),
            contract_value=max(0, contract_value), billing_cycle=billing_cycle if billing_cycle in {"Mensual", "Anual", "Único"} else "Anual",
            owner=owner.strip() or "Equipo comercial", terms_snapshot=terms_snapshot.strip(), created_by=str(user["email"]),
        )
        session.add(contract)
        add_audit(session, organization.id, str(user["email"]), "CREAR", "Contrato de servicio", contract.reference, detail=contract.title)
        session.commit()
        set_flash(request, f"Contrato {contract.reference} creado en borrador.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/contratos/{contract_id}/firmar")
    def sign_service_contract(
        contract_id: int, request: Request, signed_by: str = Form(...), signed_email: str = Form(...),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        contract = session.get(ServiceContract, contract_id)
        if not contract:
            raise HTTPException(404, "Contrato no encontrado")
        if contract.signature_hash:
            raise HTTPException(409, "El contrato ya tiene una firma registrada")
        signed_at = datetime.now(UTC)
        contract.signed_by = signed_by.strip()
        contract.signed_email = signed_email.strip().lower()
        contract.signed_at = signed_at
        contract.signature_hash = _contract_signature_hash(contract, contract.signed_by, contract.signed_email, signed_at)
        contract.status = "Vigente"
        add_audit(session, contract.organization_id, str(user["email"]), "FIRMAR", "Contrato de servicio", contract.reference, new_value=contract.signature_hash)
        session.commit()
        set_flash(request, f"Firma contractual registrada para {contract.reference}.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/contratos/{contract_id}/estado")
    def update_contract_status(
        contract_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        contract = session.get(ServiceContract, contract_id)
        if not contract:
            raise HTTPException(404, "Contrato no encontrado")
        allowed = {"Borrador", "Vigente", "Suspendido", "Terminado", "Renovado"}
        if status not in allowed:
            raise HTTPException(400, "Estado contractual inválido")
        previous = contract.status
        contract.status = status
        add_audit(session, contract.organization_id, str(user["email"]), "ACTUALIZAR", "Contrato de servicio", contract.reference, previous_value=previous, new_value=status)
        session.commit()
        set_flash(request, f"Estado de {contract.reference} actualizado a {status}.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/contratos/{contract_id}/renovar")
    def renew_service_contract(
        contract_id: int, request: Request, start_date: str = Form(...), end_date: str = Form(...),
        contract_value: float = Form(...), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        contract = session.get(ServiceContract, contract_id)
        if not contract:
            raise HTTPException(404, "Contrato no encontrado")
        renewal_number = int(session.scalar(select(func.count()).select_from(ServiceContract).where(ServiceContract.parent_contract_id == contract.id)) or 0) + 1
        reference = f"{contract.reference}-R{renewal_number}"
        while session.scalar(select(ServiceContract).where(ServiceContract.reference == reference)):
            renewal_number += 1
            reference = f"{contract.reference}-R{renewal_number}"
        renewed = ServiceContract(
            organization_id=contract.organization_id, proposal_id=contract.proposal_id, parent_contract_id=contract.id,
            reference=reference, title=contract.title, version=f"{renewal_number + 1}.0", status="Borrador",
            start_date=parse_date(start_date), end_date=parse_date(end_date), renewal_type=contract.renewal_type,
            auto_renew=contract.auto_renew, notice_days=contract.notice_days, contract_value=max(0, contract_value),
            billing_cycle=contract.billing_cycle, owner=contract.owner, terms_snapshot=contract.terms_snapshot,
            created_by=str(user["email"]),
        )
        contract.status = "Renovado"
        session.add(renewed)
        add_audit(session, contract.organization_id, str(user["email"]), "RENOVAR", "Contrato de servicio", contract.reference, new_value=reference)
        session.commit()
        set_flash(request, f"Renovación {reference} creada como nueva versión contractual.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/ordenes/nueva")
    def create_service_order(
        request: Request, organization_id: int = Form(...), contract_id: str = Form(""), reference: str = Form(""),
        title: str = Form(...), service_type: str = Form("Implementación"), description: str = Form(""),
        planned_start: str = Form(""), planned_end: str = Form(""), owner: str = Form("Equipo de implementación"),
        acceptance_criteria: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")
        contract = session.get(ServiceContract, int(contract_id)) if contract_id.strip().isdigit() else None
        if contract and contract.organization_id != organization.id:
            raise HTTPException(409, "El contrato no corresponde a la organización seleccionada")
        normalized_reference = reference.strip().upper() or _order_reference(session)
        if session.scalar(select(ServiceOrder).where(ServiceOrder.reference == normalized_reference)):
            raise HTTPException(409, "La referencia de orden ya existe")
        order = ServiceOrder(
            organization_id=organization.id, contract_id=contract.id if contract else None,
            reference=normalized_reference, title=title.strip(), service_type=service_type.strip() or "Implementación",
            description=description.strip(), status="Planeada", planned_start=parse_date(planned_start) if planned_start else None,
            planned_end=parse_date(planned_end) if planned_end else None, owner=owner.strip() or "Equipo de implementación",
            acceptance_criteria=acceptance_criteria.strip(), notes=notes.strip(), created_by=str(user["email"]),
        )
        session.add(order)
        add_audit(session, organization.id, str(user["email"]), "CREAR", "Orden de servicio", order.reference, detail=order.title)
        session.commit()
        set_flash(request, f"Orden {order.reference} creada.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/ordenes/{order_id}/estado")
    def update_service_order(
        order_id: int, request: Request, status: str = Form(...), notes: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        order = session.get(ServiceOrder, order_id)
        if not order:
            raise HTTPException(404, "Orden de servicio no encontrada")
        allowed = {"Planeada", "En ejecución", "Bloqueada", "Entregada", "Aceptada", "Cancelada"}
        if status not in allowed:
            raise HTTPException(400, "Estado de orden inválido")
        previous = order.status
        order.status = status
        order.notes = notes.strip() or order.notes
        if status in {"Entregada", "Aceptada"} and not order.delivered_at:
            order.delivered_at = datetime.now(UTC)
        if status == "Aceptada":
            order.accepted_at = datetime.now(UTC)
        add_audit(session, order.organization_id, str(user["email"]), "ACTUALIZAR", "Orden de servicio", order.reference, previous_value=previous, new_value=status)
        session.commit()
        set_flash(request, f"Orden {order.reference} actualizada a {status}.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/cobros/recurrente")
    def generate_recurring_invoice(
        request: Request, subscription_id: int = Form(...), period_start: str = Form(...), period_end: str = Form(...),
        due_date: str = Form(...), reference: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        subscription = session.scalar(
            select(OrganizationSubscription)
            .where(OrganizationSubscription.id == subscription_id)
            .options(selectinload(OrganizationSubscription.plan), selectinload(OrganizationSubscription.organization))
        )
        if not subscription or not subscription.plan:
            raise HTTPException(404, "Suscripción no encontrada")
        start = parse_date(period_start)
        end = parse_date(period_end)
        due = parse_date(due_date)
        normalized_reference = reference.strip().upper() or f"REC-{subscription.organization_id}-{start.strftime('%Y%m')}-{subscription.id}"
        if session.scalar(select(BillingInvoice).where(BillingInvoice.reference == normalized_reference)):
            raise HTTPException(409, "Ya existe un cobro para esa referencia")
        if subscription.custom_monthly_fee is not None:
            amount = subscription.custom_monthly_fee if subscription.billing_cycle == "Mensual" else subscription.custom_monthly_fee * 12
        elif subscription.billing_cycle == "Mensual":
            amount = subscription.plan.monthly_fee
        else:
            amount = subscription.plan.annual_fee
        invoice = BillingInvoice(
            organization_id=subscription.organization_id, subscription_id=subscription.id, reference=normalized_reference,
            period_start=start, period_end=end, amount=max(0, amount), status="Pendiente", issued_at=date.today(),
            due_date=due, notes=notes.strip() or "Cobro recurrente generado desde la suscripción. No constituye factura electrónica.",
        )
        session.add(invoice)
        session.flush()
        session.add(BillingDocumentRecord(
            organization_id=subscription.organization_id, invoice_id=invoice.id,
            document_type="Documento de cobro interno", internal_reference=f"DOC-{invoice.reference}",
            provider="Sin integración", status="Pendiente de integración", issued_at=invoice.issued_at,
            notes="Registro pendiente de emisión mediante proveedor tributario autorizado.", created_by=str(user["email"]),
        ))
        add_audit(session, subscription.organization_id, str(user["email"]), "GENERAR", "Cobro recurrente", invoice.reference, new_value=f"{invoice.amount:.2f}")
        session.commit()
        set_flash(request, f"Cobro {invoice.reference} generado por ${format_number(invoice.amount, 0)} COP.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/cartera/nueva")
    def create_collection_action(
        request: Request, invoice_id: int = Form(...), action_type: str = Form("Recordatorio"),
        channel: str = Form("Correo"), recipient: str = Form(""), due_at: str = Form(""), notes: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        invoice = session.get(BillingInvoice, invoice_id)
        if not invoice:
            raise HTTPException(404, "Cobro no encontrado")
        action = CollectionAction(
            organization_id=invoice.organization_id, invoice_id=invoice.id, action_type=action_type.strip() or "Recordatorio",
            channel=channel.strip() or "Correo", recipient=recipient.strip(), due_at=parse_date(due_at) if due_at else None,
            status="Pendiente", notes=notes.strip(), created_by=str(user["email"]),
        )
        session.add(action)
        add_audit(session, invoice.organization_id, str(user["email"]), "CREAR", "Gestión de cartera", invoice.reference, detail=action.action_type)
        session.commit()
        set_flash(request, "Gestión de cartera programada.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/cartera/{action_id}/completar")
    def complete_collection_action(
        action_id: int, request: Request, result: str = Form(...), invoice_status: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        action = session.get(CollectionAction, action_id)
        if not action:
            raise HTTPException(404, "Gestión de cartera no encontrada")
        action.status = "Completada"
        action.result = result.strip()
        action.completed_at = datetime.now(UTC)
        if invoice_status in {"Pendiente", "Pagada", "Vencida", "Anulada"}:
            action.invoice.status = invoice_status
            if invoice_status == "Pagada":
                action.invoice.paid_at = datetime.now(UTC)
        add_audit(session, action.organization_id, str(user["email"]), "COMPLETAR", "Gestión de cartera", action.invoice.reference, detail=action.result)
        session.commit()
        set_flash(request, "Gestión de cartera completada.")
        return RedirectResponse("/operacion-comercial", status_code=303)

    @app.post("/operacion-comercial/documentos/{document_id}/actualizar")
    def update_billing_document(
        document_id: int, request: Request, status: str = Form(...), provider: str = Form(""),
        external_number: str = Form(""), issued_at: str = Form(""), cufe: str = Form(""),
        document_url: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        document = session.get(BillingDocumentRecord, document_id)
        if not document:
            raise HTTPException(404, "Documento de cobro no encontrado")
        allowed = {"Borrador", "Pendiente de integración", "Emitido externamente", "Rechazado", "Anulado"}
        if status not in allowed:
            raise HTTPException(400, "Estado documental inválido")
        document.status = status
        document.provider = provider.strip() or document.provider
        document.external_number = external_number.strip()
        document.issued_at = parse_date(issued_at) if issued_at else document.issued_at
        document.cufe = cufe.strip()
        document.document_url = document_url.strip()
        document.notes = notes.strip()
        add_audit(session, document.organization_id, str(user["email"]), "ACTUALIZAR", "Documento de cobro", document.internal_reference, new_value=document.status)
        session.commit()
        set_flash(request, f"Documento {document.internal_reference} actualizado.")
        return RedirectResponse("/operacion-comercial", status_code=303)