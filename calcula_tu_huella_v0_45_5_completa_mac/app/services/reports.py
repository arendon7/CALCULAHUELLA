from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..database import Inventory, ReportArtifact, add_audit
from ..reporting import create_report_artifact


def generate_report(
    session: Session,
    inventory: Inventory,
    report_type: str,
    *,
    actor_email: str,
) -> ReportArtifact:
    artifact = create_report_artifact(session, inventory, report_type, actor_email)
    if inventory.status not in {"Aprobado", "Cerrado"}:
        artifact.status = "Borrador"
    add_audit(
        session,
        inventory.organization_id,
        actor_email,
        "GENERAR",
        "Informe",
        artifact.report_type,
        artifact.file_name,
    )
    return artifact


def approve_report(
    session: Session,
    artifact: ReportArtifact,
    *,
    organization_id: int,
    actor_email: str,
) -> ReportArtifact:
    artifact.status = "Aprobado"
    artifact.approved_by = actor_email
    artifact.approved_at = datetime.now(UTC)
    add_audit(
        session,
        organization_id,
        actor_email,
        "APROBAR",
        "Informe",
        artifact.report_type,
        artifact.file_name,
    )
    return artifact
