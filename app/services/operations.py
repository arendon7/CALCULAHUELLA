from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..database import OperationalIncident
from ..repositories.operations import get_operational_incident


def acknowledge_incident(session: Session, organization_id: int, incident_id: int, user_email: str) -> OperationalIncident | None:
    incident = get_operational_incident(session, organization_id, incident_id)
    if not incident:
        return None
    incident.status = "Reconocido"
    incident.acknowledged_by = user_email
    incident.acknowledged_at = datetime.now(UTC)
    return incident


def resolve_incident(session: Session, organization_id: int, incident_id: int, user_email: str) -> OperationalIncident | None:
    incident = get_operational_incident(session, organization_id, incident_id)
    if not incident:
        return None
    incident.status = "Resuelto"
    incident.resolved_by = user_email
    incident.resolved_at = datetime.now(UTC)
    return incident
