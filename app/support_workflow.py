from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from .database import SupportMessage, SupportTicket

PRIORITY_SLA_HOURS = {
    "Crítica": 4,
    "Alta": 12,
    "Normal": 36,
    "Baja": 72,
}

CATEGORY_ROUTING = {
    "Duda metodológica": "Equipo metodológico",
    "Requerimiento de información": "Responsable de datos",
    "Revisión de factor": "Revisor metodológico",
    "Problema técnico": "Equipo de plataforma",
    "Acompañamiento inicial": "Éxito del cliente",
    "Facturación y cuenta": "Administración",
    "Soporte funcional": "Equipo de soporte",
}

OPEN_STATUSES = {"Abierto", "En gestión", "Esperando cliente", "Esperando equipo", "En revisión", "Bloqueado"}
CLOSED_STATUSES = {"Resuelto", "Cerrado"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def route_assignment(category: str) -> str:
    return CATEGORY_ROUTING.get(category, "Equipo de soporte")


def response_deadline(priority: str, created_at: datetime | None = None) -> datetime:
    base = created_at or utc_now()
    return base + timedelta(hours=PRIORITY_SLA_HOURS.get(priority, PRIORITY_SLA_HOURS["Normal"]))


def ensure_reference(ticket: SupportTicket) -> str:
    if ticket.public_reference:
        return ticket.public_reference
    year = (ticket.created_at or utc_now()).year
    suffix = ticket.id or 0
    ticket.public_reference = f"CTH-{year}-{suffix:05d}"
    return ticket.public_reference


def add_support_message(
    session: Session,
    ticket: SupportTicket,
    *,
    author_email: str,
    author_role: str,
    body: str,
    message_type: str = "Mensaje",
    visible_to_client: bool = True,
) -> SupportMessage:
    normalized = body.strip()
    if not normalized:
        raise ValueError("El mensaje no puede estar vacío")
    message = SupportMessage(
        ticket_id=ticket.id,
        author_email=author_email,
        author_role=author_role,
        message_type=message_type,
        body=normalized,
        visible_to_client=visible_to_client,
        created_at=utc_now(),
    )
    ticket.last_message_at = message.created_at
    session.add(message)
    return message


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def ticket_overdue(ticket: SupportTicket, now: datetime | None = None) -> bool:
    if ticket.status in CLOSED_STATUSES or ticket.response_due_at is None:
        return False
    current = now or utc_now()
    due = _aware(ticket.response_due_at)
    return bool(due and due < current)


def ticket_waiting_days(ticket: SupportTicket, now: datetime | None = None) -> int:
    current = now or utc_now()
    origin = _aware(ticket.last_message_at or ticket.created_at) or current
    return max(0, (current - origin).days)


def ticket_context(ticket: SupportTicket) -> list[dict[str, str]]:
    context: list[dict[str, str]] = []
    if ticket.inventory:
        context.append({"label": "Inventario", "value": ticket.inventory.name, "href": f"/inventarios/{ticket.inventory.id}"})
    if ticket.source:
        context.append({"label": "Fuente", "value": ticket.source.name, "href": f"/fuentes/{ticket.source.id}"})
    if ticket.activity_data:
        record = ticket.activity_data
        context.append({
            "label": "Dato",
            "value": f"{record.value:g} {record.unit} · {record.period_start.isoformat()}",
            "href": f"/fuentes/{record.source_id}#conversacion-factor-{record.id}",
        })
    return context


def support_summary(tickets: Iterable[SupportTicket]) -> dict[str, int]:
    rows = list(tickets)
    open_rows = [ticket for ticket in rows if ticket.status in OPEN_STATUSES]
    return {
        "open": len(open_rows),
        "critical": sum(1 for ticket in open_rows if ticket.priority in {"Alta", "Crítica"}),
        "closed": sum(1 for ticket in rows if ticket.status in CLOSED_STATUSES),
        "overdue": sum(1 for ticket in open_rows if ticket_overdue(ticket)),
        "waiting_client": sum(1 for ticket in open_rows if ticket.status == "Esperando cliente"),
        "methodology": sum(1 for ticket in open_rows if ticket.category in {"Duda metodológica", "Revisión de factor"}),
    }


def status_class(status: str) -> str:
    if status in CLOSED_STATUSES:
        return "success"
    if status in {"Esperando cliente", "Esperando equipo"}:
        return "neutral"
    return "warning"
