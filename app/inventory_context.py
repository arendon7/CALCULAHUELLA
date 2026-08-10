from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .accounting import is_gross_source
from .db.models import (
    ActivityData,
    ActivityIndicator,
    EmissionSource,
    Inventory,
    InventoryFacility,
    ReductionAction,
    ReductionScenario,
    ReductionScenarioAction,
    VerificationFinding,
)


def get_inventory(session: Session, user: dict[str, object], inventory_id: int | None = None) -> Inventory:
    query = (
        select(Inventory)
        .where(Inventory.organization_id == int(user["organization_id"]))
        .options(
            selectinload(Inventory.sources).selectinload(EmissionSource.facility),
            selectinload(Inventory.sources).selectinload(EmissionSource.activity_records).selectinload(ActivityData.evidence),
            selectinload(Inventory.sources).selectinload(EmissionSource.activity_records).selectinload(ActivityData.calculations),
            selectinload(Inventory.sources).selectinload(EmissionSource.evidence_documents),
            selectinload(Inventory.facility_links).selectinload(InventoryFacility.facility),
            selectinload(Inventory.requests),
            selectinload(Inventory.documents),
            selectinload(Inventory.observations),
            selectinload(Inventory.decisions),
            selectinload(Inventory.indicators).selectinload(ActivityIndicator.facility),
            selectinload(Inventory.reduction_actions).selectinload(ReductionAction.source),
            selectinload(Inventory.reports),
            selectinload(Inventory.targets),
            selectinload(Inventory.reduction_scenarios).selectinload(ReductionScenario.action_links).selectinload(ReductionScenarioAction.action),
            selectinload(Inventory.verification_findings).selectinload(VerificationFinding.source),
        )
    )
    if inventory_id is not None:
        query = query.where(Inventory.id == inventory_id)
    else:
        query = query.order_by(Inventory.start_date.desc(), Inventory.id.desc()).limit(1)
    inventory = session.scalar(query)
    if not inventory:
        raise HTTPException(404, "Inventario no encontrado")
    return inventory

def inventory_metrics(inventory: Inventory) -> dict[str, object]:
    included_sources = [source for source in inventory.sources if is_gross_source(source)]
    total = round(sum(source.emissions for source in included_sources), 1)
    scopes = {scope: round(sum(source.emissions for source in included_sources if source.scope == scope), 1) for scope in (1, 2, 3)}
    completeness = round(sum(source.progress for source in included_sources) / max(len(included_sources), 1))
    monthly = {month: 0.0 for month in range(1, 13)}
    for source in included_sources:
        for record in source.activity_records:
            if record.period_start.year != inventory.base_year:
                continue
            monthly[record.period_start.month] += sum(
                calculation.co2e_kg for calculation in record.calculations if calculation.status == "Calculado"
            ) / 1000
    month_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    monthly_series = [
        {"month": month_labels[month - 1], "value": round(monthly[month], 2)}
        for month in range(1, 13)
    ]
    max_monthly = max((item["value"] for item in monthly_series), default=0) or 1
    for item in monthly_series:
        item["height"] = round(item["value"] / max_monthly * 100, 1) if max_monthly else 0
    return {
        "total": total,
        "scopes": scopes,
        "completeness": completeness,
        "monthly_series": monthly_series,
        "has_monthly_data": any(item["value"] > 0 for item in monthly_series),
        "source_max": max((source.emissions for source in included_sources), default=0) or 1,
    }

def ensure_inventory_editable(inventory: Inventory) -> None:
    if inventory.locked or inventory.status == "Cerrado":
        raise HTTPException(409, "El inventario está cerrado e inmutable. Debes crear una nueva versión para modificarlo.")

def get_source_for_user(session: Session, user: dict[str, object], source_id: int) -> EmissionSource:
    source = session.scalar(
        select(EmissionSource)
        .join(Inventory)
        .where(EmissionSource.id == source_id, Inventory.organization_id == int(user["organization_id"]))
        .options(selectinload(EmissionSource.inventory))
    )
    if not source:
        raise HTTPException(404, "Fuente no encontrada")
    return source
