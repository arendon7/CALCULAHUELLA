from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit_locking import acquire_audit_chain_lock
from .db.models import AuditEvent
from .security import get_request_id


def audit_event_digest(event: AuditEvent, previous_hash: str | None = None) -> str:
    created_at = event.created_at
    if created_at and created_at.tzinfo is not None:
        created_at = created_at.astimezone(UTC).replace(tzinfo=None)
    created = created_at.isoformat(timespec="microseconds") if created_at else ""
    values = [
        str(event.organization_id), event.user_email, event.action, event.entity_type,
        event.entity_label, event.detail or "", event.previous_value or "",
        event.new_value or "", event.reason or "", event.request_id or "",
        created, previous_hash if previous_hash is not None else (event.previous_hash or ""),
    ]
    return hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()


def backfill_audit_chain(session: Session) -> int:
    updated = 0
    organization_ids = list(session.scalars(select(AuditEvent.organization_id).distinct()))
    for organization_id in organization_ids:
        previous_hash = ""
        events = list(session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id)
        ))
        for event in events:
            expected = audit_event_digest(event, previous_hash)
            if not event.event_hash:
                event.previous_hash = previous_hash
                event.event_hash = expected
                updated += 1
            previous_hash = event.event_hash or expected
    return updated


def add_audit(
    session: Session,
    organization_id: int,
    user_email: str,
    action: str,
    entity_type: str,
    entity_label: str,
    detail: str = "",
    previous_value: str = "",
    new_value: str = "",
    reason: str = "",
) -> None:
    acquire_audit_chain_lock(session, organization_id)
    session.flush()
    previous = session.scalar(
        select(AuditEvent)
        .where(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    created_at = datetime.now(UTC)
    event = AuditEvent(
        organization_id=organization_id,
        user_email=user_email,
        action=action,
        entity_type=entity_type,
        entity_label=entity_label,
        detail=detail,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        request_id=get_request_id(),
        previous_hash=previous.event_hash if previous and previous.event_hash else "",
        created_at=created_at,
    )
    event.event_hash = audit_event_digest(event)
    session.add(event)
