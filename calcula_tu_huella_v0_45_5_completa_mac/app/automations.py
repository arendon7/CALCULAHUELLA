from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from .calculations import recalculate_inventory
from .database import (
    AppUser,
    AutomationRun,
    DataRequest,
    Inventory,
    OrganizationMembership,
    ReviewObservation,
    ScheduledAutomation,
    SupplierDataRequest,
)
from .notifications import create_notification, get_or_create_preference, process_pending_notifications

AUTOMATION_TYPES = [
    "Recordatorio de solicitudes",
    "Seguimiento de observaciones",
    "Seguimiento de proveedores",
    "Resumen ejecutivo",
    "Recalcular inventario",
    "Procesar notificaciones",
]
CADENCES = ["Diaria", "Semanal", "Mensual", "Manual"]
ROLE_OPTIONS = ["Administrador", "Consultor", "Cliente", "Revisor", "Verificador"]


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_roles(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return [str(item) for item in parsed if str(item)]
    except (TypeError, ValueError, json.JSONDecodeError):
        return ["Administrador", "Consultor"]


def calculate_next_run(automation: ScheduledAutomation, after: datetime | None = None) -> datetime | None:
    if not automation.active or automation.cadence == "Manual":
        return None
    after = _aware_utc(after) or datetime.now(UTC)
    try:
        zone = ZoneInfo(automation.timezone or "America/Bogota")
    except ZoneInfoNotFoundError:
        zone = UTC
    local_after = after.astimezone(zone)
    try:
        hour, minute = [int(part) for part in (automation.schedule_time or "08:00").split(":", 1)]
    except (TypeError, ValueError):
        hour, minute = 8, 0
    candidate = datetime.combine(local_after.date(), time(hour=max(0, min(hour, 23)), minute=max(0, min(minute, 59))), tzinfo=zone)

    if automation.cadence == "Diaria":
        if candidate <= local_after:
            candidate += timedelta(days=1)
    elif automation.cadence == "Semanal":
        target_weekday = automation.weekday if automation.weekday is not None else 0
        delta = (target_weekday - local_after.weekday()) % 7
        candidate += timedelta(days=delta)
        if candidate <= local_after:
            candidate += timedelta(days=7)
    elif automation.cadence == "Mensual":
        day = max(1, min(automation.month_day or 1, 28))
        candidate = candidate.replace(day=day)
        if candidate <= local_after:
            year = candidate.year + (1 if candidate.month == 12 else 0)
            month = 1 if candidate.month == 12 else candidate.month + 1
            candidate = candidate.replace(year=year, month=month, day=day)
    else:
        return None
    return candidate.astimezone(UTC)


def _users_for_roles(session: Session, organization_id: int, roles: list[str]) -> list[AppUser]:
    memberships = list(session.scalars(select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
        OrganizationMembership.role.in_(roles),
    )))
    if memberships:
        user_ids = [item.user_id for item in memberships]
        return list(session.scalars(select(AppUser).where(AppUser.id.in_(user_ids), AppUser.active.is_(True))))
    return list(session.scalars(select(AppUser).where(
        AppUser.organization_id == organization_id,
        AppUser.role.in_(roles),
        AppUser.active.is_(True),
    )))


def _notify(session: Session, automation: ScheduledAutomation, title: str, message: str, link: str, priority: str = "Normal") -> int:
    roles = _parse_roles(automation.recipient_roles)
    users = _users_for_roles(session, automation.organization_id, roles)
    created = 0
    for user in users:
        preference = get_or_create_preference(session, user.id)
        create_notification(
            session,
            automation.organization_id,
            title,
            message,
            user_id=user.id,
            link=link,
            category="Automatización",
            priority=priority,
            email_requested=preference.email_enabled,
        )
        created += 1
    return created


def execute_automation(session: Session, automation: ScheduledAutomation, *, triggered_by: str = "programación") -> AutomationRun:
    run = AutomationRun(automation_id=automation.id, status="En ejecución", started_at=datetime.now(UTC))
    session.add(run)
    session.flush()
    processed = 0
    details: list[str] = []
    today = date.today()
    threshold = today + timedelta(days=max(0, automation.days_before))
    inventory = session.get(Inventory, automation.inventory_id) if automation.inventory_id else None

    try:
        if automation.automation_type == "Recordatorio de solicitudes":
            query = select(DataRequest).join(Inventory).where(
                Inventory.organization_id == automation.organization_id,
                DataRequest.status.in_(["Pendiente", "En preparación", "Enviado"]),
                DataRequest.due_date <= threshold,
            )
            if automation.inventory_id:
                query = query.where(DataRequest.inventory_id == automation.inventory_id)
            rows = list(session.scalars(query.order_by(DataRequest.due_date)))
            for item in rows:
                overdue = item.due_date < today
                processed += _notify(
                    session,
                    automation,
                    f"{'Vencida' if overdue else 'Próxima a vencer'}: {item.title}",
                    f"Responsable: {item.requested_to}. Fecha límite: {item.due_date.strftime('%d/%m/%Y')}. Estado: {item.status}.",
                    "/informacion",
                    "Alta" if overdue else "Normal",
                )
            details.append(f"{len(rows)} solicitudes identificadas")

        elif automation.automation_type == "Seguimiento de observaciones":
            query = select(ReviewObservation).join(Inventory).where(
                Inventory.organization_id == automation.organization_id,
                ReviewObservation.status != "Cerrada",
                ReviewObservation.due_date.is_not(None),
                ReviewObservation.due_date <= threshold,
            )
            if automation.inventory_id:
                query = query.where(ReviewObservation.inventory_id == automation.inventory_id)
            rows = list(session.scalars(query.order_by(ReviewObservation.due_date)))
            for item in rows:
                processed += _notify(
                    session,
                    automation,
                    f"Observación pendiente: {item.title}",
                    f"Severidad {item.severity}. Responsable: {item.assigned_to or 'sin asignar'}. Vence: {item.due_date.strftime('%d/%m/%Y')}.",
                    "/control",
                    "Alta" if item.severity in {"Mayor", "Crítica"} else "Normal",
                )
            details.append(f"{len(rows)} observaciones identificadas")

        elif automation.automation_type == "Seguimiento de proveedores":
            query = select(SupplierDataRequest).join(SupplierDataRequest.campaign).join(Inventory).where(
                Inventory.organization_id == automation.organization_id,
                SupplierDataRequest.status.in_(["Pendiente", "Enviada"]),
                SupplierDataRequest.due_date <= threshold,
            )
            if automation.inventory_id:
                query = query.where(Inventory.id == automation.inventory_id)
            rows = list(session.scalars(query.order_by(SupplierDataRequest.due_date)))
            if rows:
                processed += _notify(
                    session,
                    automation,
                    "Seguimiento de proveedores pendiente",
                    f"Hay {len(rows)} solicitudes de alcance 3 próximas a vencer o vencidas.",
                    "/cadena-valor",
                    "Alta",
                )
            details.append(f"{len(rows)} solicitudes a proveedores identificadas")

        elif automation.automation_type == "Resumen ejecutivo":
            inventories = [inventory] if inventory else list(session.scalars(select(Inventory).where(Inventory.organization_id == automation.organization_id)))
            for item in inventories:
                if not item:
                    continue
                total = round(sum(source.emissions for source in item.sources if source.included), 2)
                open_observations = len([obs for obs in item.observations if obs.status != "Cerrada"])
                processed += _notify(
                    session,
                    automation,
                    f"Resumen ejecutivo · {item.name}",
                    f"Emisiones: {total:,.2f} tCO₂e. Avance: {item.progress} %. Observaciones abiertas: {open_observations}.",
                    f"/inventarios/{item.id}",
                )
            details.append(f"{len(inventories)} inventarios resumidos")

        elif automation.automation_type == "Recalcular inventario":
            inventories = [inventory] if inventory else list(session.scalars(select(Inventory).where(Inventory.organization_id == automation.organization_id, Inventory.locked.is_(False))))
            for item in inventories:
                if item:
                    recalculate_inventory(session, item)
                    processed += 1
            details.append(f"{processed} inventarios recalculados")

        elif automation.automation_type == "Procesar notificaciones":
            result = process_pending_notifications(session, limit=100)
            processed = result["processed"]
            details.append(f"{result['sent']} correos entregados; {result['failed']} con error")
        else:
            raise ValueError("Tipo de automatización no soportado")

        run.status = "Ejecutado"
        run.items_processed = processed
        run.summary = "; ".join(details) or "Ejecución completada"
    except Exception as exc:
        run.status = "Error"
        run.summary = str(exc)
    finally:
        run.finished_at = datetime.now(UTC)
        automation.last_run_at = run.finished_at
        automation.next_run_at = calculate_next_run(automation, run.finished_at)
        session.flush()
    return run


def process_due_automations(session: Session, limit: int = 25) -> dict[str, int]:
    now = datetime.now(UTC)
    rows = list(session.scalars(select(ScheduledAutomation).where(
        ScheduledAutomation.active.is_(True),
        ScheduledAutomation.next_run_at.is_not(None),
        ScheduledAutomation.next_run_at <= now,
    ).order_by(ScheduledAutomation.next_run_at).limit(limit)))
    executed = 0
    errors = 0
    for item in rows:
        run = execute_automation(session, item)
        executed += 1
        if run.status == "Error":
            errors += 1
    session.commit()
    return {"due": len(rows), "executed": executed, "errors": errors}


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
