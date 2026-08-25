from __future__ import annotations

from copy import deepcopy

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .calculations import source_calculation_summary
from .database import (
    ActivityData,
    ActivityFactorSelection,
    EmissionCalculation,
    EmissionFactorVersion,
    EmissionSource,
    SourceFactorAssignment,
    get_db,
)


_SCOPED_NAV_BY_ACTIVE = {
    "information": "informacion",
    "calculations": "calculos",
    "analysis": "analisis",
    "reduction": "reduccion",
    "reports": "reportes",
    "delivery": "entrega-profesional",
}


def _navigation_for_inventory(navigation: dict[str, object], inventory_id: int) -> dict[str, object]:
    scoped = deepcopy(navigation)
    root = f"/inventarios/{inventory_id}"
    for group_name in ("core", "advanced", "internal"):
        for section in scoped.get(group_name, ()):
            for item in section.get("items", ()):
                suffix = _SCOPED_NAV_BY_ACTIVE.get(str(item.get("active", "")))
                if suffix:
                    item["href"] = f"{root}/{suffix}"
    return scoped


def register_scoped_source_routes(
    app,
    templates,
    common_context,
    require_user,
    get_inventory,
) -> None:
    @app.get("/inventarios/{inventory_id}/fuentes/{source_id}", response_class=HTMLResponse)
    def scoped_source_trace(
        inventory_id: int,
        source_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user, inventory_id)
        source = session.scalar(
            select(EmissionSource)
            .where(
                EmissionSource.id == source_id,
                EmissionSource.inventory_id == inventory.id,
            )
            .options(
                selectinload(EmissionSource.facility),
                selectinload(EmissionSource.activity_records).selectinload(ActivityData.evidence),
                selectinload(EmissionSource.activity_records)
                .selectinload(ActivityData.factor_selections)
                .selectinload(ActivityFactorSelection.factor_version)
                .selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.activity_records)
                .selectinload(ActivityData.factor_selections)
                .selectinload(ActivityFactorSelection.factor_version)
                .selectinload(EmissionFactorVersion.gas),
                selectinload(EmissionSource.activity_records)
                .selectinload(ActivityData.calculations)
                .selectinload(EmissionCalculation.factor_version)
                .selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.activity_records)
                .selectinload(ActivityData.calculations)
                .selectinload(EmissionCalculation.factor_version)
                .selectinload(EmissionFactorVersion.gas),
                selectinload(EmissionSource.evidence_documents),
                selectinload(EmissionSource.factor_assignments)
                .selectinload(SourceFactorAssignment.factor_version)
                .selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.factor_assignments)
                .selectinload(SourceFactorAssignment.factor_version)
                .selectinload(EmissionFactorVersion.gas),
            )
        )
        if source is None:
            raise HTTPException(404, "Fuente no encontrada en este inventario")

        records = sorted(source.activity_records, key=lambda item: (item.period_start, item.id))
        assignments = [item for item in source.factor_assignments if item.active]
        selections = [
            selection
            for record in records
            for selection in record.factor_selections
            if selection.active
        ]
        summary = source_calculation_summary(session, source.id)
        total_activity = round(sum(item.value for item in records), 6)

        context = common_context(
            request,
            session,
            user,
            "calculations",
            inventory=inventory,
            source=source,
            records=records,
            documents=source.evidence_documents,
            assignments=assignments,
            selections=selections,
            summary=summary,
            total_activity=total_activity,
            scoped_workspace=True,
            scoped_source=True,
        )
        context["navigation"] = _navigation_for_inventory(context["navigation"], inventory.id)
        return templates.TemplateResponse(
            request=request,
            name="source_scoped.html",
            context=context,
        )
