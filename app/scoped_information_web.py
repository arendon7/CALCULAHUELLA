from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .data_request_status import open_data_requests
from .database import ActivityData, DataRequest, EmissionSource, EvidenceDocument, get_db


def register_scoped_information_routes(
    app,
    templates,
    common_context,
    require_user,
    get_inventory,
) -> None:
    """Register the read-only inventory-scoped data/evidence view from ADR-002."""

    @app.get("/inventarios/{inventory_id}/informacion", response_class=HTMLResponse)
    def scoped_information_page(
        inventory_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user, inventory_id)
        requests = list(
            session.scalars(
                select(DataRequest)
                .where(DataRequest.inventory_id == inventory.id)
                .order_by(DataRequest.due_date, DataRequest.id)
            )
        )
        documents = list(
            session.scalars(
                select(EvidenceDocument)
                .where(EvidenceDocument.inventory_id == inventory.id)
                .order_by(EvidenceDocument.uploaded_at.desc(), EvidenceDocument.id.desc())
            )
        )
        records = list(
            session.scalars(
                select(ActivityData)
                .join(EmissionSource)
                .where(EmissionSource.inventory_id == inventory.id)
                .options(
                    selectinload(ActivityData.source).selectinload(EmissionSource.facility),
                    selectinload(ActivityData.evidence),
                )
                .order_by(ActivityData.period_start.desc(), ActivityData.created_at.desc(), ActivityData.id.desc())
            )
        )
        quality_counts = {
            level: sum(1 for item in records if item.quality_level == level)
            for level in ("A", "B", "C", "D")
        }
        return templates.TemplateResponse(
            request=request,
            name="information_scoped.html",
            context=common_context(
                request,
                session,
                user,
                "information",
                inventory=inventory,
                requests=requests,
                open_requests=open_data_requests(requests),
                documents=documents,
                records=records,
                sources=inventory.sources,
                quality_counts=quality_counts,
                scoped_workspace=True,
            ),
        )
