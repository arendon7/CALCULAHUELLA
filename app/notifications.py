from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import INSTANCE_DIR, settings
from .database import AppUser, Notification, NotificationPreference, OrganizationMembership

OUTBOX_DIR = INSTANCE_DIR / "mail_outbox"
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_preference(session: Session, user_id: int) -> NotificationPreference:
    preference = session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    if preference:
        return preference
    preference = NotificationPreference(user_id=user_id)
    session.add(preference)
    session.flush()
    return preference


def create_notification(
    session: Session,
    organization_id: int,
    title: str,
    message: str,
    *,
    user_id: int | None = None,
    link: str = "",
    category: str = "Sistema",
    priority: str = "Normal",
    email_requested: bool = False,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        user_id=user_id,
        title=title.strip(),
        message=message.strip(),
        link=link.strip(),
        category=category,
        priority=priority,
        email_requested=email_requested,
        status="Pendiente" if email_requested else "Entregada",
    )
    session.add(notification)
    session.flush()
    return notification


def notify_roles(
    session: Session,
    organization_id: int,
    roles: set[str],
    title: str,
    message: str,
    *,
    link: str = "",
    category: str = "Flujo",
    priority: str = "Normal",
    email_requested: bool = False,
) -> list[Notification]:
    memberships = list(session.scalars(select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.role.in_(roles),
        OrganizationMembership.active.is_(True),
    )))
    if memberships:
        user_ids = [item.user_id for item in memberships]
        users = list(session.scalars(select(AppUser).where(AppUser.id.in_(user_ids), AppUser.active.is_(True))))
    else:
        users = list(session.scalars(select(AppUser).where(
            AppUser.organization_id == organization_id,
            AppUser.role.in_(roles),
            AppUser.active.is_(True),
        )))
    created: list[Notification] = []
    for user in users:
        preference = get_or_create_preference(session, user.id)
        created.append(create_notification(
            session, organization_id, title, message, user_id=user.id, link=link,
            category=category, priority=priority,
            email_requested=email_requested and preference.email_enabled,
        ))
    return created


def _deliver_email(recipient: str, title: str, message: str, link: str) -> tuple[bool, str]:
    body = message
    if link:
        body += f"\n\nAbrir: {settings.public_base_url}{link}"
    if settings.email_backend == "file":
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        path = OUTBOX_DIR / f"{stamp}_{recipient.replace('@', '_at_')}.txt"
        path.write_text(f"Para: {recipient}\nAsunto: {title}\n\n{body}\n", encoding="utf-8")
        return True, str(path.relative_to(INSTANCE_DIR))
    if settings.email_backend == "smtp":
        email = EmailMessage()
        email["From"] = settings.smtp_from
        email["To"] = recipient
        email["Subject"] = title
        email.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(email)
            return True, "SMTP"
        except Exception as exc:  # pragma: no cover - depende de SMTP externo
            return False, str(exc)
    return False, "EMAIL_BACKEND desactivado"


def process_pending_notifications(session: Session, limit: int = 50) -> dict[str, int]:
    pending = list(session.scalars(select(Notification).where(
        Notification.email_requested.is_(True),
        Notification.status.in_(["Pendiente", "Error"]),
    ).order_by(Notification.created_at).limit(limit)))
    sent = 0
    failed = 0
    for notification in pending:
        user = session.get(AppUser, notification.user_id) if notification.user_id else None
        if not user:
            notification.status = "Error"
            notification.delivery_detail = "Usuario destinatario no disponible"
            failed += 1
            continue
        ok, detail = _deliver_email(user.email, notification.title, notification.message, notification.link)
        notification.delivery_detail = detail
        notification.delivery_attempts += 1
        notification.last_attempt_at = datetime.now(UTC)
        if ok:
            notification.status = "Entregada"
            notification.delivered_at = datetime.now(UTC)
            sent += 1
        else:
            notification.status = "Error"
            failed += 1
    session.flush()
    return {"processed": len(pending), "sent": sent, "failed": failed}
