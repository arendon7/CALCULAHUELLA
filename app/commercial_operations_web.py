from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import (
    BillingChargeBreakdown,
    BillingDocumentRecord,
    BillingInvoice,
    CollectionAction,
    CommercialProposal,
    ContractSignatureSnapshot,
    Organization,
    OrganizationSubscription,
    ServiceContract,
    ServiceOrder,
)
from .revenue_operations import (
    CONTRACT_SIGNATURE_VERSION,
    INVOICE_BASE_BEFORE_TAX,
    INVOICE_TOTAL_WITH_TAX,
    contract_signature_hash,
    contract_signature_source,
    parse_nonnegative_number,
    validate_date_window,
)


VALID_CONTRACT_BILLING_CYCLES = {"Mensual", "Anual", "Único"}
VALID_RENEWAL_TYPES = {"Anual", "Mensual", "Por acuerdo", "No renovable"}


def _contract_reference(session: Session) -> str:
    year = date.today().year
    current = session.scalar(select(func.count()).select_from(ServiceContract)) or 0
    return f"CTR-{year}-{int(current) + 1:04d}"


def _order_reference(session: Session) -> str:
    year = date.today().year
    current = session.scalar(select(func.count()).select_from(ServiceOrder)) or 0
    return f"OS-{year}-{int(current) + 1:04d}"


def _route_date(parse_date, raw: str, label: str) -> date:
    try:
        return parse_date(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, f"{label} no es una fecha válida") from exc


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
        invoices = list(session.scalars(
            select(BillingInvoice).order_by(BillingInvoice.issued_at.desc(), BillingInvoice.id.desc())
        ))
        invoice_ids = [item.id for item in invoices]
        breakdown_by_invoice = {}
        if invoice_ids:
            breakdown_by_invoice = {
                item.invoice_id: item
                for item in session.scalars(
                    select(BillingChargeBreakdown).where(BillingChargeBreakdown.invoice_id.in_(invoice_ids))
                )
            }
        contract_ids = [item.id for item in contracts]
        signature_by_contract = {}
        if contract_ids:
            signature_by_contract = {
                item.contract_id: item
                for item in session.scalars(
                    select(ContractSignatureSnapshot).where(ContractSignatureSnapshot.contract_id.in_(contract_ids))
                )
            }
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
        overdue = [
            item for item in invoices
            if item.status in {"Pendiente", "Vencida"} and item.due_date and item.due_date < today
        ]
        outstanding = [item for item in invoices if item.status in {"Pendiente", "Vencida"}]
        renewals = [
            item for item in contracts
            if item.status == "Vigente" and item.end_date and 0 <= (item.end_date - today).days <= 120
        ]

        def known_total(items: list[BillingInvoice]) -> float:
            return sum(
                breakdown_by_invoice[item.id].total_amount or 0
                for item in items
                if item.id in breakdown_by_invoice
                and breakdown_by_invoice[item.id].amount_semantics == INVOICE_TOTAL_WITH_TAX
                and breakdown_by_invoice[item.id].total_amount is not None
            )

        pending_tax_base = sum(
            breakdown_by_invoice[item.id].net_amount or 0
            for item in outstanding
            if item.id in breakdown_by_invoice
            and breakdown_by_invoice[item.id].amount_semantics == INVOICE_BASE_BEFORE_TAX
            and breakdown_by_invoice[item.id].net_amount is not None
        )
        legacy_outstanding = sum(1 for item in outstanding if item.id not in breakdown_by_invoice)
        summary = {
            "active_contracts": sum(1 for item in contracts if item.status == "Vigente"),
            "open_orders": sum(1 for item in orders if item.status not in {"Aceptada", "Cancelada"}),
            "outstanding_amount": round(known_total(outstanding), 2),
            "overdue_amount": round(known_total(overdue), 2),
            "pending_tax_base": round(pending_tax_base, 2),
            "legacy_outstanding": legacy_outstanding,
            "renewals": len(renewals),
        }
        return templates.TemplateResponse(request, "commercial_operations.html", common_context(
            request, session, user, "commercial_operations",
            contracts=contracts, orders=orders, invoices=invoices, actions=actions, documents=documents,
            subscriptions=subscriptions, organizations=organizations, org_map=org_map, proposals=proposals,
            overdue=overdue, renewals=renewals, summary=summary, today=today,
            breakdown_by_invoice=breakdown_by_invoice, signature_by_contract=signature_by_contract,
        ))

    @app.post("/operacion-comercial/contratos/nuevo")
    def create_service_contract(
        request: Request,
        organization_id: int = Form(...), proposal_id: str = Form(""), reference: str = Form(""),
        title: str = Form(...), start_date: str = Form(...), end_date: str = Form(""),
        renewal_type: str = Form("Anual"), auto_renew: str | None = Form(None), notice_days: str = Form("30"),
        contract_value: str = Form("0"), billing_cycle: str = Form("Anual"), owner: str = Form("Equipo comercial"),
        terms_snapshot: str = Form(""), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")

        proposal = None
        if proposal_id.strip():
            if not proposal_id.strip().isdigit():
                raise HTTPException(400, "La propuesta seleccionada no es válida")
            proposal = session.get(CommercialProposal, int(proposal_id))
            if not proposal:
                raise HTTPException(404, "Propuesta no encontrada")
            if proposal.status != "Aceptada":
                raise HTTPException(409, "Solo puede vincularse una propuesta aceptada")
            if proposal.organization_id != organization.id:
                raise HTTPException(409, "La propuesta no corresponde a la organización seleccionada")

        clean_title = title.strip()
        if not clean_title:
            raise HTTPException(400, "Define el título del contrato")
        if billing_cycle not in VALID_CONTRACT_BILLING_CYCLES:
            raise HTTPException(400, "Ciclo contractual inválido")
        if renewal_type not in VALID_RENEWAL_TYPES:
            raise HTTPException(400, "Tipo de renovación inválido")
        try:
            contract_value_number = parse_nonnegative_number(contract_value, "el valor contractual")
            notice_days_number = parse_nonnegative_number(notice_days, "los días de preaviso")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not notice_days_number.is_integer():
            raise HTTPException(400, "Los días de preaviso deben ser un número entero")

        start = _route_date(parse_date, start_date, "La fecha inicial")
        end = _route_date(parse_date, end_date, "La fecha final") if end_date else None
        try:
            validate_date_window(start, end, label="vigencia contractual")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

        normalized_reference = reference.strip().upper() or _contract_reference(session)
        if session.scalar(select(ServiceContract).where(ServiceContract.reference == normalized_reference)):
            raise HTTPException(409, "La referencia contractual ya existe")
        contract = ServiceContract(
            organization_id=organization.id, proposal_id=proposal.id if proposal else None,
            reference=normalized_reference, title=clean_title, version="1.0", status="Borrador",
            start_date=start, end_date=end, renewal_type=renewal_type, auto_renew=bool(auto_renew),
            notice_days=int(notice_days_number), contract_value=contract_value_number, billing_cycle=billing_cycle,
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
        if contract.signature_hash or session.scalar(
            select(ContractSignatureSnapshot).where(ContractSignatureSnapshot.contract_id == contract.id)
        ):
            raise HTTPException(409, "El contrato ya tiene una firma registrada")
        clean_signed_by = signed_by.strip()
        clean_signed_email = signed_email.strip().lower()
        if not clean_signed_by or "@" not in clean_signed_email:
            raise HTTPException(400, "Identidad de firma incompleta")
        signed_at = datetime.now(UTC)
        canonical_payload = contract_signature_source(contract, clean_signed_by, clean_signed_email, signed_at)
        signature_hash = contract_signature_hash(contract, clean_signed_by, clean_signed_email, signed_at)
        contract.signed_by = clean_signed_by
        contract.signed_email = clean_signed_email
        contract.signed_at = signed_at
        contract.signature_hash = signature_hash
        contract.status = "Vigente"
        session.add(ContractSignatureSnapshot(
            contract_id=contract.id,
            signature_version=CONTRACT_SIGNATURE_VERSION,
            canonical_payload=canonical_payload,
            payload_hash=signature_hash,
        ))
        add_audit(session, contract.organization_id, str(user["email"]), "FIRMAR", "Contrato de servicio", contract.reference, new_value=signature_hash)
        session.commit()
        set_flash(request, f"Firma contractual registrada para {contract.reference} con snapshot v{CONTRACT_SIGNATURE_VERSION}.")
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
        contract_value: str = Form(...), session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_commercial")
        contract = session.get(ServiceContract, contract_id)
        if not contract:
            raise HTTPException(404, "Contrato no encontrado")
        if contract.status not in {"Vigente", "Terminado"}:
            raise HTTPException(409, "Solo pueden renovarse contratos vigentes o terminados")
        try:
            renewal_value = parse_nonnegative_number(contract_value, "el valor de renovación")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        start = _route_date(parse_date, start_date, "La fecha inicial")
        end = _route_date(parse_date, end_date, "La fecha final")
        try:
            validate_date_window(start, end, label="renovación")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

        renewal_number = int(session.scalar(
            select(func.count()).select_from(ServiceContract).where(ServiceContract.parent_contract_id == contract.id)
        ) or 0) + 1
        reference = f"{contract.reference}-R{renewal_number}"
        while session.scalar(select(ServiceContract).where(ServiceContract.reference == reference)):
            renewal_number += 1
            reference = f"{contract.reference}-R{renewal_number}"
        renewed = ServiceContract(
            organization_id=contract.organization_id, proposal_id=contract.proposal_id, parent_contract_id=contract.id,
            reference=reference, title=contract.title, version=f"{renewal_number + 1}.0", status="Borrador",
            start_date=start, end_date=end, renewal_type=contract.renewal_type,
            auto_renew=contract.auto_renew, notice_days=contract.notice_days, contract_value=renewal_value,
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
        if subscription.billing_cycle not in {"Mensual", "Anual"}:
            raise HTTPException(409, "La suscripción no tiene un ciclo recurrente soportado")
        start = _route_date(parse_date, period_start, "El inicio del periodo")
        end = _route_date(parse_date, period_end, "El fin del periodo")
        due = _route_date(parse_date, due_date, "El vencimiento")
        try:
            validate_date_window(start, end, label="periodo de cobro")
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if due < end:
            raise HTTPException(400, "El vencimiento no puede ser anterior al fin del periodo cobrado")

        normalized_reference = reference.strip().upper() or f"REC-{subscription.organization_id}-{start.strftime('%Y%m')}-{subscription.id}"
        if session.scalar(select(BillingInvoice).where(BillingInvoice.reference == normalized_reference)):
            raise HTTPException(409, "Ya existe un cobro para esa referencia")
        raw_amount = (
            subscription.custom_monthly_fee if subscription.custom_monthly_fee is not None
            else subscription.plan.monthly_fee
        )
        if subscription.billing_cycle == "Anual":
            raw_amount = (
                subscription.custom_monthly_fee * 12
                if subscription.custom_monthly_fee is not None
                else subscription.plan.annual_fee
            )
        try:
            base_amount = parse_nonnegative_number(raw_amount, "la base recurrente")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

        mandatory_note = (
            "Registro recurrente por la base contractual antes de impuesto. La liquidación tributaria final está pendiente; "
            "este registro no constituye factura electrónica."
        )
        user_note = notes.strip()
        invoice_notes = mandatory_note if not user_note else f"{mandatory_note}\nNota operativa: {user_note}"
        invoice = BillingInvoice(
            organization_id=subscription.organization_id, subscription_id=subscription.id, reference=normalized_reference,
            period_start=start, period_end=end, amount=base_amount, status="Pendiente", issued_at=date.today(),
            due_date=due, notes=invoice_notes,
        )
        session.add(invoice)
        session.flush()
        session.add(BillingChargeBreakdown(
            invoice_id=invoice.id,
            charge_type="Recurrente",
            amount_semantics=INVOICE_BASE_BEFORE_TAX,
            net_amount=base_amount,
            tax_rate_snapshot=None,
            tax_amount=None,
            total_amount=None,
            source_reference=f"SUB-{subscription.id}",
            classification_note=(
                "Base recurrente conocida. No existe una tasa tributaria contractual persistida en la suscripción; "
                "no se infiere un total a cobrar."
            ),
        ))
        session.add(BillingDocumentRecord(
            organization_id=subscription.organization_id, invoice_id=invoice.id,
            document_type="Documento de cobro interno", internal_reference=f"DOC-{invoice.reference}",
            provider="Sin integración", status="Pendiente de integración", issued_at=invoice.issued_at,
            notes="Registro pendiente de liquidación/emisión mediante proveedor tributario autorizado.", created_by=str(user["email"]),
        ))
        add_audit(session, subscription.organization_id, str(user["email"]), "GENERAR", "Cobro recurrente", invoice.reference, new_value=f"base={invoice.amount:.2f}; impuesto=pendiente")
        session.commit()
        set_flash(request, f"Registro {invoice.reference} generado por base ${format_number(invoice.amount, 0)} COP antes de impuesto.")
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
        if invoice_status == "Pagada":
            breakdown = session.scalar(
                select(BillingChargeBreakdown).where(BillingChargeBreakdown.invoice_id == action.invoice_id)
            )
            if breakdown and breakdown.amount_semantics == INVOICE_BASE_BEFORE_TAX:
                raise HTTPException(
                    409,
                    "Este registro conserva solo la base antes de impuesto. Liquida/emite el documento tributario antes de marcar un total como pagado.",
                )
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
        clean_provider = provider.strip()
        clean_external_number = external_number.strip()
        issue_date = _route_date(parse_date, issued_at, "La fecha de emisión") if issued_at else document.issued_at
        if status == "Emitido externamente":
            if not clean_provider or clean_provider == "Sin integración":
                raise HTTPException(400, "Identifica el proveedor que realizó la emisión externa")
            if not clean_external_number:
                raise HTTPException(400, "Registra el número externo del documento emitido")
            if not issue_date:
                raise HTTPException(400, "Registra la fecha de emisión externa")
        document.status = status
        document.provider = clean_provider or document.provider
        document.external_number = clean_external_number
        document.issued_at = issue_date
        document.cufe = cufe.strip()
        document.document_url = document_url.strip()
        document.notes = notes.strip()
        add_audit(session, document.organization_id, str(user["email"]), "ACTUALIZAR", "Documento de cobro", document.internal_reference, new_value=document.status)
        session.commit()
        set_flash(request, f"Documento {document.internal_reference} actualizado.")
        return RedirectResponse("/operacion-comercial", status_code=303)
