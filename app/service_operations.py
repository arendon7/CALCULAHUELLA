from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import (
    AppUser,
    BillingInvoice,
    EvidenceDocument,
    Facility,
    Inventory,
    OrganizationMembership,
    OrganizationSubscription,
    ServicePlan,
    SupportTicket,
    UserInvitation,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

METRICS = {
    "users": ("Usuarios activos", "max_users"),
    "facilities": ("Sedes activas", "max_facilities"),
    "inventories": ("Inventarios", "max_inventories"),
    "storage": ("Almacenamiento MB", "max_storage_mb"),
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def active_subscription(session: Session, organization_id: int) -> OrganizationSubscription | None:
    return session.scalar(
        select(OrganizationSubscription)
        .where(OrganizationSubscription.organization_id == organization_id)
        .options(selectinload(OrganizationSubscription.plan))
    )


def pending_invitations(session: Session, organization_id: int) -> list[UserInvitation]:
    now = utcnow()
    rows = list(session.scalars(
        select(UserInvitation)
        .where(
            UserInvitation.organization_id == organization_id,
            UserInvitation.status == "Pendiente",
        )
        .order_by(UserInvitation.created_at.desc())
    ))
    changed = False
    for item in rows:
        expires_at = _aware(item.expires_at)
        if expires_at and expires_at < now:
            item.status = "Vencida"
            changed = True
    if changed:
        session.flush()
    return [item for item in rows if item.status == "Pendiente"]


def capacity_snapshot(session: Session, organization_id: int) -> dict[str, object]:
    subscription = active_subscription(session, organization_id)
    plan = subscription.plan if subscription else None
    active_users = int(session.scalar(select(func.count(OrganizationMembership.id)).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
    )) or 0)
    invitations = pending_invitations(session, organization_id)
    facilities = int(session.scalar(select(func.count(Facility.id)).where(
        Facility.organization_id == organization_id,
        Facility.active.is_(True),
    )) or 0)
    inventories = int(session.scalar(select(func.count(Inventory.id)).where(
        Inventory.organization_id == organization_id,
    )) or 0)
    storage_bytes = float(session.scalar(
        select(func.coalesce(func.sum(EvidenceDocument.file_size), 0))
        .join(Inventory, EvidenceDocument.inventory_id == Inventory.id)
        .where(Inventory.organization_id == organization_id)
    ) or 0)
    raw_values = {
        "users": active_users + len(invitations),
        "facilities": facilities,
        "inventories": inventories,
        "storage": round(storage_bytes / (1024 * 1024), 2),
    }
    metrics: dict[str, dict[str, object]] = {}
    for code, (label, limit_attr) in METRICS.items():
        limit = float(getattr(plan, limit_attr, 0) or 0)
        value = float(raw_values[code])
        percentage = round(value / limit * 100) if limit else 0
        status = "blocked" if limit and value >= limit else "warning" if limit and percentage >= 80 else "ok"
        metrics[code] = {
            "code": code,
            "label": label,
            "value": value,
            "limit": limit,
            "percentage": min(100, percentage),
            "status": status,
            "available": max(0, limit - value) if limit else None,
        }
    subscription_status = subscription.status if subscription else "Sin plan"
    operational = subscription_status in {"Activa", "Prueba"}
    alerts: list[dict[str, str]] = []
    if not subscription:
        alerts.append({"level": "warning", "title": "Cuenta sin plan", "detail": "Asigna un plan antes de ampliar usuarios, sedes o inventarios."})
    elif not operational:
        alerts.append({"level": "danger", "title": f"Suscripción {subscription_status.lower()}", "detail": "Las ampliaciones de capacidad están bloqueadas hasta regularizar la cuenta."})
    for item in metrics.values():
        if item["status"] == "blocked":
            alerts.append({"level": "danger", "title": f"Límite de {str(item['label']).lower()} alcanzado", "detail": "Desactiva recursos no utilizados o cambia de plan."})
        elif item["status"] == "warning":
            alerts.append({"level": "warning", "title": f"Capacidad de {str(item['label']).lower()} al {item['percentage']}%", "detail": "Planifica la ampliación antes de alcanzar el límite."})
    return {
        "subscription": subscription,
        "plan": plan,
        "operational": operational,
        "metrics": metrics,
        "pending_invitations": invitations,
        "active_users": active_users,
        "alerts": alerts,
    }


def ensure_capacity(session: Session, organization_id: int, metric: str, increment: float = 1) -> None:
    snapshot = capacity_snapshot(session, organization_id)
    subscription = snapshot["subscription"]
    if subscription and subscription.status not in {"Activa", "Prueba"}:
        raise HTTPException(409, "La suscripción no permite ampliar capacidad. Revisa el estado de la cuenta.")
    item = snapshot["metrics"].get(metric)
    if not item or not item["limit"]:
        return
    if float(item["value"]) + increment > float(item["limit"]):
        raise HTTPException(409, f"El plan alcanzó el límite de {str(item['label']).lower()}. Cambia de plan o libera capacidad.")


def ensure_invitation_acceptance(session: Session, organization_id: int) -> None:
    """Confirma que una invitación reservada todavía puede convertirse en acceso activo.

    La invitación pendiente ya ocupa un cupo. Por eso no se suma un usuario adicional;
    solo se bloquea cuando la cuenta dejó de estar operativa o un cambio de plan dejó
    el consumo reservado por encima del nuevo límite.
    """
    snapshot = capacity_snapshot(session, organization_id)
    subscription = snapshot["subscription"]
    if subscription and subscription.status not in {"Activa", "Prueba"}:
        raise HTTPException(409, "La invitación no puede aceptarse mientras la suscripción esté suspendida o cancelada.")
    item = snapshot["metrics"].get("users")
    if not item or not item["limit"]:
        return
    if float(item["value"]) > float(item["limit"]):
        raise HTTPException(409, "El plan cambió y ya no tiene capacidad para aceptar esta invitación. Libera un cupo o amplía el plan.")


def create_invitation(
    session: Session,
    organization_id: int,
    email: str,
    role: str,
    invited_by: str,
    name: str = "",
    days_valid: int = 7,
) -> tuple[UserInvitation, str]:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise HTTPException(400, "Correo de invitación inválido")
    ensure_capacity(session, organization_id, "users", 1)
    existing_membership = session.scalar(
        select(OrganizationMembership)
        .join(AppUser, OrganizationMembership.user_id == AppUser.id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            AppUser.email == normalized,
        )
    )
    if existing_membership:
        raise HTTPException(409, "El correo ya pertenece a esta organización")
    for previous in list(session.scalars(select(UserInvitation).where(
        UserInvitation.organization_id == organization_id,
        UserInvitation.email == normalized,
        UserInvitation.status == "Pendiente",
    ))):
        previous.status = "Reemplazada"
        previous.cancelled_at = utcnow()
    raw_token = secrets.token_urlsafe(32)
    invitation = UserInvitation(
        organization_id=organization_id,
        email=normalized,
        invited_name=name.strip(),
        role=role,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        status="Pendiente",
        invited_by=invited_by,
        expires_at=utcnow() + timedelta(days=max(1, min(days_valid, 30))),
    )
    session.add(invitation)
    session.flush()
    return invitation, raw_token


def resolve_invitation(session: Session, raw_token: str) -> UserInvitation | None:
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = session.scalar(
        select(UserInvitation)
        .where(UserInvitation.token_hash == digest)
        .options(selectinload(UserInvitation.organization))
    )
    if not invitation:
        return None
    if invitation.status == "Pendiente" and _aware(invitation.expires_at) < utcnow():
        invitation.status = "Vencida"
        session.commit()
    return invitation


def operation_summary(session: Session, organization_id: int) -> dict[str, object]:
    snapshot = capacity_snapshot(session, organization_id)
    open_tickets = int(session.scalar(select(func.count(SupportTicket.id)).where(
        SupportTicket.organization_id == organization_id,
        SupportTicket.status.notin_(["Cerrado", "Resuelto", "Cancelado"]),
    )) or 0)
    overdue_invoices = list(session.scalars(select(BillingInvoice).where(
        BillingInvoice.organization_id == organization_id,
        BillingInvoice.status.in_(["Pendiente", "Vencida"]),
        BillingInvoice.due_date.is_not(None),
        BillingInvoice.due_date < date.today(),
    ).order_by(BillingInvoice.due_date)))
    actions: list[dict[str, str]] = []
    if snapshot["alerts"]:
        for alert in snapshot["alerts"][:3]:
            actions.append({"title": alert["title"], "detail": alert["detail"], "route": "/cuenta-servicio"})
    if overdue_invoices:
        actions.append({"title": f"{len(overdue_invoices)} cobro(s) vencido(s)", "detail": "Revisa el estado administrativo de la cuenta.", "route": "/cuenta-servicio"})
    if open_tickets:
        actions.append({"title": f"{open_tickets} requerimiento(s) abierto(s)", "detail": "Prioriza respuestas y compromisos pendientes.", "route": "/soporte"})
    if snapshot["pending_invitations"]:
        actions.append({"title": f"{len(snapshot['pending_invitations'])} invitación(es) pendiente(s)", "detail": "Confirma aceptación o cancela accesos que ya no se requieran.", "route": "/usuarios"})
    if not actions:
        actions.append({"title": "Operación del servicio al día", "detail": "No hay alertas comerciales o de capacidad que requieran acción inmediata.", "route": "/dashboard"})
    return {
        **snapshot,
        "open_tickets": open_tickets,
        "overdue_invoices": overdue_invoices,
        "actions": actions,
    }
