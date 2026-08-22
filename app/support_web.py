from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import add_audit, get_db
from .db.models import ActivityData, EmissionSource, Inventory, SupportTicket
from .notifications import notify_roles
from .support_workflow import (
    CLOSED_STATUSES,
    OPEN_STATUSES,
    add_support_message,
    ensure_reference,
    response_deadline,
    route_assignment,
    status_class,
    support_summary,
    ticket_context,
    ticket_overdue,
    ticket_waiting_days,
)


def register_support_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
) -> None:
    @app.get("/soporte", response_class=HTMLResponse)
    def support_center(
        request: Request,
        status: str = "",
        category: str = "",
        q: str = "",
        ticket_id: int | None = None,
        inventory_id: int | None = None,
        source_id: int | None = None,
        activity_data_id: int | None = None,
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        organization_id = int(user["organization_id"])
        if ticket_id is not None:
            ticket_exists = session.scalar(
                select(SupportTicket.id).where(
                    SupportTicket.id == ticket_id,
                    SupportTicket.organization_id == organization_id,
                )
            )
            if not ticket_exists:
                raise HTTPException(404, "Caso no encontrado")
            return RedirectResponse(f"/soporte/{ticket_id}", status_code=303)

        query = (
            select(SupportTicket)
            .where(SupportTicket.organization_id == organization_id)
            .options(
                selectinload(SupportTicket.messages),
                selectinload(SupportTicket.inventory),
                selectinload(SupportTicket.source),
                selectinload(SupportTicket.activity_data),
            )
            .order_by(SupportTicket.updated_at.desc(), SupportTicket.created_at.desc())
        )
        all_tickets = list(session.scalars(query))
        tickets = all_tickets
        if status:
            tickets = [item for item in tickets if item.status == status]
        if category:
            tickets = [item for item in tickets if item.category == category]
        normalized_q = q.strip().casefold()
        if normalized_q:
            tickets = [
                item for item in tickets
                if normalized_q in " ".join((item.public_reference, item.subject, item.description, item.assigned_to)).casefold()
            ]
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == organization_id).order_by(Inventory.created_at.desc())))
        sources = list(session.scalars(
            select(EmissionSource).join(Inventory).where(Inventory.organization_id == organization_id).order_by(EmissionSource.name)
        ))
        prefill_record = None
        if activity_data_id:
            prefill_record = session.scalar(
                select(ActivityData).join(EmissionSource).join(Inventory).where(
                    ActivityData.id == activity_data_id, Inventory.organization_id == organization_id,
                )
            )
        return templates.TemplateResponse(request, "support.html", common_context(
            request, session, user, "support", tickets=tickets, stats=support_summary(all_tickets),
            status_class=status_class, ticket_overdue=ticket_overdue, ticket_waiting_days=ticket_waiting_days,
            ticket_context=ticket_context, filters={"status": status, "category": category, "q": q},
            inventories=inventories, sources=sources, prefill={
                "inventory_id": inventory_id or (prefill_record.source.inventory_id if prefill_record and prefill_record.source else None),
                "source_id": source_id or (prefill_record.source_id if prefill_record else None),
                "activity_data_id": activity_data_id or None,
                "category": "Revisión de factor" if activity_data_id else "",
            },
        ))


    @app.get("/soporte/{ticket_id}", response_class=HTMLResponse)
    def support_ticket_detail(ticket_id: int, request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        ticket = session.scalar(
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id, SupportTicket.organization_id == int(user["organization_id"]))
            .options(
                selectinload(SupportTicket.messages),
                selectinload(SupportTicket.inventory),
                selectinload(SupportTicket.source),
                selectinload(SupportTicket.activity_data),
            )
        )
        if not ticket:
            raise HTTPException(404, "Caso no encontrado")
        visible_messages = [
            message for message in ticket.messages
            if message.visible_to_client or user["role"] != "Cliente"
        ]
        context = common_context(
            request,
            session,
            user,
            "support",
            ticket=ticket,
            messages=visible_messages,
            context_items=ticket_context(ticket),
            overdue=ticket_overdue(ticket),
            waiting_days=ticket_waiting_days(ticket),
            status_class=status_class(ticket.status),
        )
        if ticket.inventory is not None:
            context["inventory"] = ticket.inventory
        return templates.TemplateResponse(request, "support_detail.html", context)


    @app.post("/soporte/nuevo")
    def create_support_ticket(
        request: Request,
        subject: str = Form(...),
        description: str = Form(...),
        category: str = Form("Soporte funcional"),
        request_type: str = Form("Consulta"),
        priority: str = Form("Normal"),
        desired_outcome: str = Form(""),
        due_date: str = Form(""),
        inventory_id: int | None = Form(None),
        source_id: int | None = Form(None),
        activity_data_id: int | None = Form(None),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_support")
        organization_id = int(user["organization_id"])
        normalized_subject = subject.strip()
        normalized_description = description.strip()
        if len(normalized_subject) < 6 or len(normalized_description) < 12:
            set_flash(request, "Describe el asunto y la necesidad con suficiente detalle.", "error")
            return RedirectResponse("/soporte#nuevo-caso", status_code=303)
        inventory = session.scalar(select(Inventory).where(Inventory.id == inventory_id, Inventory.organization_id == organization_id)) if inventory_id else None
        source = session.scalar(select(EmissionSource).join(Inventory).where(EmissionSource.id == source_id, Inventory.organization_id == organization_id)) if source_id else None
        record = session.scalar(select(ActivityData).join(EmissionSource).join(Inventory).where(ActivityData.id == activity_data_id, Inventory.organization_id == organization_id)) if activity_data_id else None
        if inventory_id and not inventory:
            raise HTTPException(400, "Inventario no válido")
        if source_id and not source:
            raise HTTPException(400, "Fuente no válida")
        if activity_data_id and not record:
            raise HTTPException(400, "Dato no válido")
        if record and source and record.source_id != source.id:
            raise HTTPException(400, "El dato no pertenece a la fuente seleccionada")
        if source and inventory and source.inventory_id != inventory.id:
            raise HTTPException(400, "La fuente no pertenece al inventario seleccionado")
        normalized_priority = priority if priority in {"Baja", "Normal", "Alta", "Crítica"} else "Normal"
        ticket = SupportTicket(
            organization_id=organization_id,
            inventory_id=inventory.id if inventory else (source.inventory_id if source else None),
            source_id=source.id if source else (record.source_id if record else None),
            activity_data_id=record.id if record else None,
            created_by=str(user["email"]),
            request_type=request_type if request_type in {"Consulta", "Requerimiento", "Incidencia", "Decisión metodológica"} else "Consulta",
            category=category,
            priority=normalized_priority,
            subject=normalized_subject,
            description=normalized_description,
            desired_outcome=desired_outcome.strip(),
            status="Abierto",
            assigned_to=route_assignment(category),
            due_date=parse_date(due_date) if due_date else None,
            response_due_at=response_deadline(normalized_priority),
            last_message_at=datetime.now(UTC),
        )
        session.add(ticket)
        session.flush()
        ensure_reference(ticket)
        add_support_message(
            session, ticket, author_email=str(user["email"]), author_role=str(user["role"]),
            body=normalized_description, message_type="Solicitud inicial", visible_to_client=True,
        )
        notify_roles(
            session, organization_id, {"Administrador", "Consultor", "Revisor"},
            f"Nuevo requerimiento {ticket.public_reference}",
            f"{ticket.subject} · prioridad {ticket.priority}", link=f"/soporte/{ticket.id}",
            category="Soporte", priority=ticket.priority,
        )
        add_audit(session, organization_id, str(user["email"]), "CREAR", "Requerimiento", ticket.public_reference, detail=ticket.description)
        session.commit()
        set_flash(request, f"Requerimiento {ticket.public_reference} creado y asignado a {ticket.assigned_to}.")
        return RedirectResponse(f"/soporte/{ticket.id}", status_code=303)


    @app.post("/soporte/{ticket_id}/mensajes")
    def add_ticket_message(
        ticket_id: int,
        request: Request,
        body: str = Form(...),
        message_type: str = Form("Mensaje"),
        visible_to_client: str | None = Form(None),
        next_status: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        ensure_capability(user, "manage_support")
        ticket = session.scalar(select(SupportTicket).where(
            SupportTicket.id == ticket_id, SupportTicket.organization_id == int(user["organization_id"]),
        ))
        if not ticket:
            raise HTTPException(404, "Caso no encontrado")
        internal = visible_to_client is None and user["role"] != "Cliente"
        if user["role"] == "Cliente":
            internal = False
            message_type = "Mensaje del cliente"
        allowed_types = {"Mensaje", "Mensaje del cliente", "Respuesta técnica", "Solicitud de información", "Nota interna", "Decisión metodológica"}
        normalized_type = message_type if message_type in allowed_types else "Mensaje"
        if internal:
            normalized_type = "Nota interna"
        try:
            add_support_message(
                session, ticket, author_email=str(user["email"]), author_role=str(user["role"]), body=body,
                message_type=normalized_type, visible_to_client=not internal,
            )
        except ValueError as exc:
            set_flash(request, str(exc), "error")
            return RedirectResponse(f"/soporte/{ticket.id}#conversacion", status_code=303)
        allowed_statuses = OPEN_STATUSES | CLOSED_STATUSES
        if next_status in allowed_statuses and user["role"] != "Cliente":
            ticket.status = next_status
        elif user["role"] == "Cliente" and ticket.status == "Esperando cliente":
            ticket.status = "En gestión"
            ticket.response_due_at = response_deadline(ticket.priority)
        ticket.closed_at = datetime.now(UTC) if ticket.status == "Cerrado" else None
        add_audit(session, int(user["organization_id"]), str(user["email"]), "MENSAJE", "Requerimiento", ticket.public_reference, detail=normalized_type)
        session.commit()
        set_flash(request, "Mensaje registrado en la conversación.")
        return RedirectResponse(f"/soporte/{ticket.id}#conversacion", status_code=303)


    @app.post("/soporte/{ticket_id}/actualizar")
    def update_support_ticket(
        ticket_id: int,
        request: Request,
        status: str = Form(...),
        assigned_to: str = Form(""),
        priority: str = Form("Normal"),
        due_date: str = Form(""),
        resolution: str = Form(""),
        session: Session = Depends(get_db),
    ):
        user = require_user(request)
        if user["role"] == "Cliente":
            raise HTTPException(403, "El cliente puede crear y responder casos, pero el equipo gestiona su estado")
        ensure_capability(user, "manage_support")
        ticket = session.scalar(select(SupportTicket).where(
            SupportTicket.id == ticket_id, SupportTicket.organization_id == int(user["organization_id"]),
        ))
        if not ticket:
            raise HTTPException(404, "Caso no encontrado")
        previous_status = ticket.status
        previous_priority = ticket.priority
        ticket.status = status if status in OPEN_STATUSES | CLOSED_STATUSES else ticket.status
        ticket.priority = priority if priority in {"Baja", "Normal", "Alta", "Crítica"} else ticket.priority
        ticket.assigned_to = assigned_to.strip() or ticket.assigned_to
        ticket.due_date = parse_date(due_date) if due_date else None
        normalized_resolution = resolution.strip()
        if normalized_resolution and normalized_resolution != ticket.resolution:
            ticket.resolution = normalized_resolution
            add_support_message(
                session, ticket, author_email=str(user["email"]), author_role=str(user["role"]),
                body=normalized_resolution, message_type="Respuesta técnica", visible_to_client=True,
            )
        if previous_priority != ticket.priority and ticket.status in OPEN_STATUSES:
            ticket.response_due_at = response_deadline(ticket.priority)
        ticket.closed_at = datetime.now(UTC) if ticket.status == "Cerrado" else None
        if previous_status != ticket.status:
            add_support_message(
                session, ticket, author_email=str(user["email"]), author_role=str(user["role"]),
                body=f"Estado actualizado de {previous_status} a {ticket.status}.",
                message_type="Cambio de estado", visible_to_client=True,
            )
        add_audit(
            session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Requerimiento",
            ticket.public_reference, previous_value=previous_status, new_value=ticket.status,
        )
        session.commit()
        set_flash(request, f"Requerimiento {ticket.public_reference} actualizado.")
        return RedirectResponse(f"/soporte/{ticket.id}", status_code=303)


    @app.get("/api/soporte/resumen")
    def support_api_summary(request: Request, session: Session = Depends(get_db)):
        user = require_user(request)
        tickets = list(session.scalars(
            select(SupportTicket).where(SupportTicket.organization_id == int(user["organization_id"])).order_by(SupportTicket.updated_at.desc())
        ))
        return {
            "version": settings.version,
            "summary": support_summary(tickets),
            "recent": [
                {
                    "id": ticket.id,
                    "reference": ticket.public_reference,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "assigned_to": ticket.assigned_to,
                    "overdue": ticket_overdue(ticket),
                }
                for ticket in tickets[:10]
            ],
        }
