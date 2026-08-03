from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .analytics import full_analysis
from .database import BenchmarkReference, ImpactSnapshot, Inventory, Organization


METRIC_LABELS = {
    "intensity_employee": "Intensidad por empleado",
    "intensity_revenue_billion": "Intensidad por ingresos",
    "intensity_production": "Intensidad por producción",
    "quality_score": "Calidad de datos",
    "evidence_coverage": "Cobertura de evidencias",
}


def latest_inventory(session: Session, organization_id: int) -> Inventory | None:
    return session.scalar(
        select(Inventory)
        .where(Inventory.organization_id == organization_id)
        .options(
            selectinload(Inventory.sources),
            selectinload(Inventory.indicators),
            selectinload(Inventory.reduction_actions),
        )
        .order_by(Inventory.start_date.desc(), Inventory.id.desc())
    )


def impact_metrics(session: Session, organization_id: int, inventory_id: int | None = None) -> dict[str, object]:
    organization = session.get(Organization, organization_id)
    if not organization:
        raise ValueError("Organización no encontrada")
    inventory = session.get(Inventory, inventory_id) if inventory_id else latest_inventory(session, organization_id)
    if not inventory or inventory.organization_id != organization_id:
        return {
            "organization": organization, "inventory": None, "total_emissions": 0.0,
            "intensity_employee": 0.0, "intensity_revenue_billion": 0.0, "intensity_production": 0.0,
            "quality_score": 0.0, "evidence_coverage": 0.0, "expected_reduction": 0.0,
            "actual_reduction": 0.0, "investment": 0.0, "annual_savings": 0.0,
            "value_per_tonne": 0.0, "impact_score": 0,
        }
    analysis = full_analysis(session, inventory)
    reduction = analysis["reduction"]
    total = float(analysis["total"] or 0)
    employees = max(organization.employees, 0)
    revenue_billion = organization.annual_revenue / 1_000_000_000 if organization.annual_revenue else 0
    intensity_employee = total / employees if employees else 0
    intensity_revenue = total / revenue_billion if revenue_billion else 0
    intensity_production = float(analysis["intensity_production"] or 0)
    quality = float(analysis["quality"]["score"] or 0)
    evidence = float(analysis["quality"]["evidence_coverage"] or 0)
    expected = float(reduction["expected_reduction"] or 0)
    actual = float(reduction["actual_reduction"] or 0)
    investment = float(reduction["investment"] or 0)
    savings = float(reduction["annual_savings"] or 0)
    value_per_tonne = savings / expected if expected else 0
    reduction_coverage = min(100.0, expected / total * 100) if total else 0
    realized_share = min(100.0, actual / expected * 100) if expected else 0
    impact_score = int(round(max(0, min(100, quality * 0.25 + evidence * 0.20 + reduction_coverage * 0.30 + realized_share * 0.25))))
    return {
        "organization": organization, "inventory": inventory, "total_emissions": round(total, 4),
        "intensity_employee": round(intensity_employee, 6),
        "intensity_revenue_billion": round(intensity_revenue, 6),
        "intensity_production": round(intensity_production, 6),
        "quality_score": round(quality, 2), "evidence_coverage": round(evidence, 2),
        "expected_reduction": round(expected, 4), "actual_reduction": round(actual, 4),
        "investment": round(investment, 2), "annual_savings": round(savings, 2),
        "value_per_tonne": round(value_per_tonne, 2), "impact_score": impact_score,
        "reduction_coverage": round(reduction_coverage, 1), "realized_share": round(realized_share, 1),
    }


def refresh_impact_snapshot(session: Session, organization_id: int, inventory_id: int | None = None, created_by: str = "sistema") -> ImpactSnapshot:
    metrics = impact_metrics(session, organization_id, inventory_id)
    inventory = metrics["inventory"]
    serializable = {key: value for key, value in metrics.items() if key not in {"organization", "inventory"}}
    snapshot = ImpactSnapshot(
        organization_id=organization_id, inventory_id=inventory.id if inventory else None,
        total_emissions=float(metrics["total_emissions"]), intensity_employee=float(metrics["intensity_employee"]),
        intensity_revenue_billion=float(metrics["intensity_revenue_billion"]),
        intensity_production=float(metrics["intensity_production"]), quality_score=float(metrics["quality_score"]),
        evidence_coverage=float(metrics["evidence_coverage"]), expected_reduction=float(metrics["expected_reduction"]),
        actual_reduction=float(metrics["actual_reduction"]), investment=float(metrics["investment"]),
        annual_savings=float(metrics["annual_savings"]), value_per_tonne=float(metrics["value_per_tonne"]),
        impact_score=int(metrics["impact_score"]), metrics_json=json.dumps(serializable, ensure_ascii=False, default=str),
        calculated_at=datetime.now(UTC), created_by=created_by,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def compare_benchmarks(metrics: dict[str, object], references: list[BenchmarkReference]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for ref in references:
        current = float(metrics.get(ref.metric_code, 0) or 0)
        target = ref.top_quartile_value
        median = ref.median_value
        if current == 0:
            status, gap = "Sin dato", None
        elif ref.lower_is_better:
            if current <= target:
                status = "Cuartil superior"
            elif current <= median:
                status = "Mejor que mediana"
            else:
                status = "Brecha"
            gap = ((current / target) - 1) * 100 if target else None
        else:
            if current >= target:
                status = "Cuartil superior"
            elif current >= median:
                status = "Mejor que mediana"
            else:
                status = "Brecha"
            gap = (1 - current / target) * 100 if target else None
        rows.append({"reference": ref, "current": current, "status": status, "gap": round(gap, 1) if gap is not None else None})
    return rows


def portfolio_comparison(session: Session, organization_ids: list[int], active_organization_id: int) -> list[dict[str, object]]:
    rows = []
    for index, organization_id in enumerate(sorted(set(organization_ids)), start=1):
        metrics = impact_metrics(session, organization_id)
        org = metrics["organization"]
        rows.append({
            "organization_id": organization_id,
            "label": "Tu organización" if organization_id == active_organization_id else f"Organización comparable {index}",
            "sector": org.sector, "total": metrics["total_emissions"],
            "intensity_employee": metrics["intensity_employee"],
            "intensity_revenue_billion": metrics["intensity_revenue_billion"],
            "quality_score": metrics["quality_score"], "impact_score": metrics["impact_score"],
            "is_active": organization_id == active_organization_id,
        })
    return sorted(rows, key=lambda item: (item["intensity_employee"] == 0, item["intensity_employee"]))
