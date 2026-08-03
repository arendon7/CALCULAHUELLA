from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .accounting import is_gross_source
from .database import (
    ActivityData,
    ActivityIndicator,
    EmissionCalculation,
    EmissionSource,
    Inventory,
    ReductionAction,
)

QUALITY_WEIGHTS = {"A": 100.0, "B": 82.0, "C": 58.0, "D": 30.0}
MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


@dataclass
class IndicatorMetric:
    indicator_type: str
    value: float
    unit: str
    aggregation: str


def inventory_total(inventory: Inventory) -> float:
    return round(sum(source.emissions for source in inventory.sources if is_gross_source(source)), 6)


def scopes_summary(inventory: Inventory) -> dict[int, float]:
    return {
        scope: round(sum(source.emissions for source in inventory.sources if is_gross_source(source) and source.scope == scope), 6)
        for scope in (1, 2, 3)
    }


def indicator_metrics(session: Session, inventory_id: int) -> dict[str, IndicatorMetric]:
    rows = list(session.scalars(select(ActivityIndicator).where(ActivityIndicator.inventory_id == inventory_id)))
    grouped: dict[str, list[ActivityIndicator]] = defaultdict(list)
    for row in rows:
        grouped[row.indicator_type].append(row)
    result: dict[str, IndicatorMetric] = {}
    for indicator_type, items in grouped.items():
        if indicator_type in {"Empleados"}:
            value = sum(item.value for item in items) / max(len(items), 1)
            aggregation = "Promedio"
        else:
            value = sum(item.value for item in items)
            aggregation = "Suma"
        result[indicator_type] = IndicatorMetric(indicator_type, value, items[0].unit, aggregation)
    return result


def quality_summary(session: Session, inventory_id: int) -> dict[str, object]:
    rows = list(
        session.scalars(
            select(ActivityData)
            .join(EmissionSource)
            .where(EmissionSource.inventory_id == inventory_id, EmissionSource.included.is_(True), EmissionSource.accounting_treatment == "Emisión bruta")
        )
    )
    counts = {level: 0 for level in ("A", "B", "C", "D")}
    supported = 0
    estimated = 0
    weighted = 0.0
    for row in rows:
        level = row.quality_level if row.quality_level in counts else "D"
        counts[level] += 1
        weighted += QUALITY_WEIGHTS[level]
        supported += int(row.evidence_id is not None)
        estimated += int(row.is_estimated)
    total = len(rows)
    return {
        "score": round(weighted / total) if total else 0,
        "counts": counts,
        "records": total,
        "evidence_coverage": round(supported / total * 100) if total else 0,
        "estimated_share": round(estimated / total * 100) if total else 0,
    }


def monthly_emissions(session: Session, inventory_id: int) -> list[dict[str, object]]:
    rows = session.execute(
        select(ActivityData.period_start, EmissionCalculation.co2e_kg)
        .join(EmissionCalculation, EmissionCalculation.activity_data_id == ActivityData.id)
        .join(EmissionSource, ActivityData.source_id == EmissionSource.id)
        .where(EmissionSource.inventory_id == inventory_id)
    ).all()
    totals = {month: 0.0 for month in range(1, 13)}
    for period_start, co2e_kg in rows:
        totals[period_start.month] += co2e_kg / 1000
    return [{"month": MONTH_NAMES[month - 1], "value": round(totals[month], 3)} for month in range(1, 13)]


def facility_summary(inventory: Inventory) -> list[dict[str, object]]:
    totals: dict[str, float] = defaultdict(float)
    for source in inventory.sources:
        if not is_gross_source(source):
            continue
        label = source.facility.name if source.facility else "Corporativo"
        totals[label] += source.emissions
    return [
        {"name": name, "emissions": round(value, 3)}
        for name, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def source_summary(inventory: Inventory) -> list[dict[str, object]]:
    total = inventory_total(inventory)
    rows = []
    for source in sorted((item for item in inventory.sources if is_gross_source(item)), key=lambda item: item.emissions, reverse=True):
        rows.append({
            "id": source.id,
            "name": source.name,
            "category": source.category,
            "scope": source.scope,
            "facility": source.facility.name if source.facility else "Corporativo",
            "emissions": round(source.emissions, 3),
            "share": round(source.emissions / total * 100, 1) if total else 0,
        })
    return rows


def historical_summary(session: Session, inventory: Inventory) -> dict[str, object]:
    inventories = list(
        session.scalars(
            select(Inventory)
            .where(Inventory.organization_id == inventory.organization_id)
            .options(selectinload(Inventory.sources), selectinload(Inventory.indicators))
            .order_by(Inventory.start_date)
        )
    )
    series = []
    for item in inventories:
        indicators = indicator_metrics(session, item.id)
        production = indicators.get("Producción")
        total = inventory_total(item)
        intensity = total / production.value if production and production.value else 0
        series.append({
            "inventory_id": item.id,
            "year": item.start_date.year,
            "total": round(total, 3),
            "production": round(production.value, 3) if production else 0,
            "intensity": round(intensity, 6),
            "status": item.status,
        })
    current_index = next((idx for idx, item in enumerate(series) if item["inventory_id"] == inventory.id), None)
    previous = series[current_index - 1] if current_index is not None and current_index > 0 else None
    current = series[current_index] if current_index is not None else None
    total_change = ((current["total"] / previous["total"] - 1) * 100) if current and previous and previous["total"] else None
    intensity_change = ((current["intensity"] / previous["intensity"] - 1) * 100) if current and previous and previous["intensity"] else None
    return {
        "series": series,
        "previous": previous,
        "current": current,
        "total_change": round(total_change, 1) if total_change is not None else None,
        "intensity_change": round(intensity_change, 1) if intensity_change is not None else None,
    }


def reduction_summary(session: Session, inventory_id: int) -> dict[str, object]:
    actions = list(
        session.scalars(
            select(ReductionAction)
            .where(ReductionAction.inventory_id == inventory_id)
            .options(selectinload(ReductionAction.source))
            .order_by(ReductionAction.priority, ReductionAction.expected_reduction.desc())
        )
    )
    expected = sum(item.expected_reduction for item in actions)
    actual = sum(item.actual_reduction for item in actions)
    investment = sum(item.investment_cost for item in actions)
    savings = sum(item.annual_savings for item in actions)
    payback = investment / savings if savings else None
    return {
        "actions": actions,
        "expected_reduction": round(expected, 3),
        "actual_reduction": round(actual, 3),
        "investment": investment,
        "annual_savings": savings,
        "payback_years": round(payback, 2) if payback is not None else None,
        "average_progress": round(sum(item.progress_percent for item in actions) / max(len(actions), 1)),
    }


def full_analysis(session: Session, inventory: Inventory) -> dict[str, object]:
    indicators = indicator_metrics(session, inventory.id)
    total = inventory_total(inventory)
    production = indicators.get("Producción")
    employees = indicators.get("Empleados")
    revenue = indicators.get("Ingresos")
    return {
        "total": total,
        "scopes": scopes_summary(inventory),
        "sources_summary": source_summary(inventory),
        "facilities_summary": facility_summary(inventory),
        "monthly": monthly_emissions(session, inventory.id),
        "quality": quality_summary(session, inventory.id),
        "indicators": indicators,
        "intensity_production": total / production.value if production and production.value else None,
        "intensity_employee": total / employees.value if employees and employees.value else None,
        "intensity_revenue": total / (revenue.value / 1_000_000) if revenue and revenue.value else None,
        "history": historical_summary(session, inventory),
        "reduction": reduction_summary(session, inventory.id),
    }
