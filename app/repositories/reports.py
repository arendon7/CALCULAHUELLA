from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import Inventory, ReportArtifact


def list_report_artifacts(session: Session, inventory_id: int) -> list[ReportArtifact]:
    return list(
        session.scalars(
            select(ReportArtifact)
            .where(ReportArtifact.inventory_id == inventory_id)
            .order_by(ReportArtifact.generated_at.desc())
        )
    )


def get_report_artifact(session: Session, organization_id: int, artifact_id: int) -> ReportArtifact | None:
    return session.scalar(
        select(ReportArtifact)
        .join(Inventory)
        .where(
            ReportArtifact.id == artifact_id,
            Inventory.organization_id == organization_id,
        )
    )
