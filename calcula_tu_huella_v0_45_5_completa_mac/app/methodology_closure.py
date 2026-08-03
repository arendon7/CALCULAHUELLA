from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .accounting import ACCOUNTING_TREATMENTS, SCOPE2_METHODS, balance_from_sources, is_gross_source, treatment_for
from .database import (
    ActivityData,
    BaseYearRecalculation,
    EmissionCalculation,
    EmissionSource,
    Inventory,
    InventoryMethodologySnapshot,
    MethodologyValidationRun,
)

POLICY_SNAPSHOT_NAME = "Cierre metodológico V0.32"
DEFAULT_POLICY: dict[str, Any] = {
    "base_year_recalculation_threshold": 5.0,
    "base_year_triggers": "Cambios estructurales, adquisiciones/desinversiones, errores materiales y cambios metodológicos significativos.",
    "biogenic_co2_policy": "Reportar por separado como partida informativa; no sumar al inventario bruto de alcance 1.",
    "removals_policy": "Reportar separadas de las emisiones brutas y sujetas a trazabilidad, permanencia y límites definidos.",
    "avoided_emissions_policy": "Reportar fuera del inventario físico y sin netear emisiones corporativas.",
    "offsets_policy": "Reportar fuera del inventario bruto; solo aplicar a declaraciones netas con instrumento verificable.",
    "scope2_policy": "Conservar location-based y market-based por separado cuando existan instrumentos contractuales aptos.",
    "uncertainty_method": "Propagación de errores por raíz de suma de cuadrados (Approach 1).",
    "status": "Borrador",
    "approved_by": "",
    "approved_at": "",
}


def _policy_from_snapshot(snapshot: InventoryMethodologySnapshot | None) -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    if snapshot and snapshot.policy_json:
        try:
            loaded = json.loads(snapshot.policy_json)
            if isinstance(loaded, dict):
                policy.update(loaded)
        except json.JSONDecodeError:
            pass
    return policy


def get_or_create_policy_snapshot(session: Session, inventory: Inventory) -> InventoryMethodologySnapshot:
    snapshot = session.scalar(
        select(InventoryMethodologySnapshot)
        .where(
            InventoryMethodologySnapshot.inventory_id == inventory.id,
            InventoryMethodologySnapshot.snapshot_name == POLICY_SNAPSHOT_NAME,
        )
        .order_by(InventoryMethodologySnapshot.id.desc())
        .limit(1)
    )
    if snapshot:
        return snapshot
    snapshot = InventoryMethodologySnapshot(
        inventory_id=inventory.id,
        snapshot_name=POLICY_SNAPSHOT_NAME,
        status="Borrador",
        methodology_name=inventory.methodology,
        methodology_version=inventory.methodology_version,
        gwp_version=inventory.gwp_version,
        consolidation_approach=inventory.consolidation_approach,
        materiality_threshold=inventory.materiality_threshold,
        policy_json=json.dumps(DEFAULT_POLICY, ensure_ascii=False),
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def save_policy(session: Session, inventory: Inventory, payload: dict[str, Any], actor: str, approve: bool = False) -> InventoryMethodologySnapshot:
    snapshot = get_or_create_policy_snapshot(session, inventory)
    policy = _policy_from_snapshot(snapshot)
    policy.update(payload)
    policy["base_year_recalculation_threshold"] = max(0.0, float(policy.get("base_year_recalculation_threshold") or 0))
    if approve:
        policy["status"] = "Aprobado"
        policy["approved_by"] = actor
        policy["approved_at"] = datetime.now(UTC).isoformat()
        snapshot.status = "Aprobado"
        snapshot.approved_by = actor
        snapshot.approved_at = datetime.now(UTC)
    else:
        policy["status"] = "Borrador"
        snapshot.status = "Borrador"
    snapshot.methodology_name = inventory.methodology
    snapshot.methodology_version = inventory.methodology_version
    snapshot.gwp_version = inventory.gwp_version
    snapshot.consolidation_approach = inventory.consolidation_approach
    snapshot.materiality_threshold = inventory.materiality_threshold
    snapshot.policy_json = json.dumps(policy, ensure_ascii=False)
    session.flush()
    return snapshot


def calculation_uncertainty(activity_uncertainty: float, factor_uncertainty: float) -> float:
    return math.sqrt(max(activity_uncertainty, 0.0) ** 2 + max(factor_uncertainty, 0.0) ** 2)


def uncertainty_summary(session: Session, inventory: Inventory) -> dict[str, Any]:
    rows = session.scalars(
        select(EmissionCalculation)
        .join(ActivityData, EmissionCalculation.activity_data_id == ActivityData.id)
        .join(EmissionSource, ActivityData.source_id == EmissionSource.id)
        .where(EmissionSource.inventory_id == inventory.id, EmissionSource.included.is_(True))
        .options(
            selectinload(EmissionCalculation.activity_data).selectinload(ActivityData.source),
            selectinload(EmissionCalculation.factor_version),
        )
    ).all()
    gross_sources = [source for source in inventory.sources if is_gross_source(source)]
    gross_rows = [row for row in rows if is_gross_source(row.activity_data.source) and row.status != "Error"]

    # La incertidumbre solo puede propagarse sobre emisiones con memoria de cálculo.
    # Las fuentes sincronizadas o agregadas sin cálculo explícito se reportan como
    # cobertura pendiente, evitando presentar un rango parcial como si fuera total.
    covered_kg = sum(abs(row.co2e_kg) for row in gross_rows)
    total_gross_kg = sum(abs(float(source.emissions or 0)) * 1000 for source in gross_sources)
    variance = sum((abs(row.co2e_kg) * max(row.uncertainty_percentage, 0) / 100) ** 2 for row in gross_rows)
    combined = math.sqrt(variance) / covered_kg * 100 if covered_kg else 0.0
    missing_calculations = sum(
        1 for row in gross_rows
        if float(row.activity_data.uncertainty_percentage or 0) <= 0
        or float(row.factor_version.uncertainty_percentage or 0) <= 0
    )
    calculated_source_ids = {row.activity_data.source_id for row in gross_rows}
    uncovered_sources = [
        source for source in gross_sources
        if abs(float(source.emissions or 0)) > 0 and source.id not in calculated_source_ids
    ]
    emission_coverage = covered_kg / total_gross_kg * 100 if total_gross_kg else 100.0
    calculation_coverage = (len(gross_rows) - missing_calculations) / max(len(gross_rows), 1) * 100
    missing = missing_calculations + len(uncovered_sources)
    return {
        "combined_percentage": round(combined, 2),
        "gross_tco2e": round(covered_kg / 1000, 6),
        "covered_tco2e": round(covered_kg / 1000, 6),
        "total_gross_tco2e": round(total_gross_kg / 1000, 6),
        "lower_tco2e": round(max(0.0, covered_kg * (1 - combined / 100)) / 1000, 6),
        "upper_tco2e": round(covered_kg * (1 + combined / 100) / 1000, 6),
        "calculations": len(gross_rows),
        "missing_uncertainty": missing,
        "missing_calculations": missing_calculations,
        "uncovered_sources": [
            {"id": source.id, "name": source.name, "emissions": round(float(source.emissions or 0), 6)}
            for source in uncovered_sources
        ],
        "coverage_percentage": round(emission_coverage, 1),
        "emission_coverage_percentage": round(emission_coverage, 1),
        "calculation_coverage_percentage": round(calculation_coverage, 1),
        "complete": missing == 0 and emission_coverage >= 99.9,
    }


def scope2_summary(inventory: Inventory) -> dict[str, Any]:
    rows = [source for source in inventory.sources if source.included and source.scope == 2 and treatment_for(source) == "Emisión bruta"]
    location = sum(source.emissions for source in rows if source.scope2_method == "Location-based")
    market = sum(source.emissions for source in rows if source.scope2_method == "Market-based")
    unclassified = [source for source in rows if source.scope2_method not in {"Location-based", "Market-based"}]
    return {
        "location_based": round(location, 6),
        "market_based": round(market, 6),
        "unclassified": unclassified,
        "sources": rows,
    }


def methodological_readiness(session: Session, inventory: Inventory, policy: dict[str, Any]) -> list[dict[str, str]]:
    validation = session.scalar(select(MethodologyValidationRun).order_by(MethodologyValidationRun.executed_at.desc(), MethodologyValidationRun.id.desc()).limit(1))
    uncertainty = uncertainty_summary(session, inventory)
    scope2 = scope2_summary(inventory)
    treatments_ok = all(treatment_for(source) in ACCOUNTING_TREATMENTS for source in inventory.sources if source.included)
    gates = [
        ("Política metodológica", policy.get("status") == "Aprobado", "Aprobar políticas de año base, partidas separadas, alcance 2 e incertidumbre."),
        ("Tratamiento contable", treatments_ok, "Clasificar cada fuente como emisión bruta, biogénica, remoción, evitada o compensación."),
        ("Alcance 2", not scope2["unclassified"], "Clasificar las fuentes de alcance 2 como location-based o market-based."),
        ("Incertidumbre", uncertainty["complete"], "Documentar incertidumbre del dato, del factor y de toda fuente bruta con emisiones."),
        ("Casos patrón", bool(validation and validation.status == "Aprobado"), "Ejecutar y aprobar la batería metodológica independiente."),
        ("Política de año base", float(policy.get("base_year_recalculation_threshold") or 0) > 0, "Definir un umbral cuantitativo de recalculo."),
    ]
    return [
        {"name": name, "status": "Aprobado" if ok else "Pendiente", "detail": detail}
        for name, ok, detail in gates
    ]


def closure_summary(session: Session, inventory: Inventory) -> dict[str, Any]:
    snapshot = get_or_create_policy_snapshot(session, inventory)
    policy = _policy_from_snapshot(snapshot)
    recalculations = session.scalars(
        select(BaseYearRecalculation)
        .where(BaseYearRecalculation.inventory_id == inventory.id)
        .order_by(BaseYearRecalculation.event_date.desc(), BaseYearRecalculation.id.desc())
    ).all()
    readiness = methodological_readiness(session, inventory, policy)
    return {
        "inventory": inventory,
        "snapshot": snapshot,
        "policy": policy,
        "balance": balance_from_sources(inventory.sources),
        "uncertainty": uncertainty_summary(session, inventory),
        "scope2": scope2_summary(inventory),
        "recalculations": recalculations,
        "readiness": readiness,
        "readiness_score": round(100 * sum(item["status"] == "Aprobado" for item in readiness) / max(len(readiness), 1)),
        "treatments": ACCOUNTING_TREATMENTS,
        "scope2_methods": SCOPE2_METHODS,
    }


def create_recalculation(
    session: Session,
    inventory: Inventory,
    *,
    trigger_type: str,
    description: str,
    previous_total_tco2e: float,
    recalculated_total_tco2e: float,
    threshold_percentage: float,
    actor: str,
) -> BaseYearRecalculation:
    change = ((recalculated_total_tco2e / previous_total_tco2e - 1) * 100) if previous_total_tco2e else 0.0
    decision = "Recalcular" if abs(change) >= threshold_percentage else "No recalcular"
    item = BaseYearRecalculation(
        inventory_id=inventory.id,
        trigger_type=trigger_type.strip(),
        description=description.strip(),
        previous_total_tco2e=max(previous_total_tco2e, 0),
        recalculated_total_tco2e=max(recalculated_total_tco2e, 0),
        change_percentage=change,
        threshold_percentage=max(threshold_percentage, 0),
        decision=decision,
        status="Pendiente",
        requested_by=actor,
    )
    session.add(item)
    session.flush()
    return item
