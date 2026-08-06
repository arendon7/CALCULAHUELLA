from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import DeploymentRehearsal, OperationalIncident


def list_deployment_rehearsals(session: Session, organization_id: int, limit: int = 20) -> list[DeploymentRehearsal]:
    return list(session.scalars(
        select(DeploymentRehearsal)
        .where(DeploymentRehearsal.organization_id == organization_id)
        .order_by(DeploymentRehearsal.started_at.desc())
        .limit(limit)
    ))


def list_operational_incidents(session: Session, organization_id: int, limit: int = 50) -> list[OperationalIncident]:
    return list(session.scalars(
        select(OperationalIncident)
        .where(OperationalIncident.organization_id == organization_id)
        .order_by(OperationalIncident.status, OperationalIncident.last_seen_at.desc())
        .limit(limit)
    ))


def get_operational_incident(session: Session, organization_id: int, incident_id: int) -> OperationalIncident | None:
    return session.scalar(select(OperationalIncident).where(
        OperationalIncident.id == incident_id,
        OperationalIncident.organization_id == organization_id,
    ))
