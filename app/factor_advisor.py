from __future__ import annotations

from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import ActivityData, EmissionFactorVersion, EmissionSource, FactorDocumentation, UnitConversion, UnitDefinition

APPLIED_SELECTION_STATUSES = {"Aprobado", "Seleccionado"}  # Seleccionado conserva compatibilidad V0.49.
PENDING_SELECTION_STATUSES = {"Propuesto", "Requiere ajuste"}


def _tokens(value: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in (value or ""))
    ignored = {"de", "del", "la", "el", "y", "en", "para", "por", "con", "un", "una"}
    return {part for part in cleaned.split() if len(part) > 2 and part not in ignored}


def unit_compatibility(session: Session, from_unit: str, to_unit: str) -> tuple[int, str, bool]:
    if from_unit == to_unit:
        return 45, "Compatibilidad directa: el dato y el factor usan la misma unidad.", True
    direct = session.scalar(select(UnitConversion).where(
        UnitConversion.from_unit == from_unit, UnitConversion.to_unit == to_unit, UnitConversion.active.is_(True)
    ))
    if direct:
        return 37, f"Conversión disponible: {from_unit} × {direct.multiplier:g} + {direct.offset:g} → {to_unit}.", True
    source_unit = session.scalar(select(UnitDefinition).where(UnitDefinition.code == from_unit, UnitDefinition.active.is_(True)))
    target_unit = session.scalar(select(UnitDefinition).where(UnitDefinition.code == to_unit, UnitDefinition.active.is_(True)))
    if source_unit and target_unit and source_unit.dimension == target_unit.dimension:
        return 18, f"Misma dimensión ({source_unit.dimension}), pero falta una conversión aprobada {from_unit} → {to_unit}.", False
    return 0, f"Unidades incompatibles: {from_unit} no conversa con {to_unit}.", False


def advise_factor(session: Session, source: EmissionSource, record: ActivityData, version: EmissionFactorVersion) -> dict[str, object]:
    unit_score, unit_note, calculable = unit_compatibility(session, record.unit, version.input_unit)
    source_tokens = _tokens(" ".join([source.name, source.category, record.notes or "", record.data_origin or ""]))
    factor_tokens = _tokens(" ".join([version.factor.name, version.factor.activity_type, version.factor.sector, version.technology_scope]))
    overlap = sorted(source_tokens & factor_tokens)
    semantic_score = min(22, len(overlap) * 7)
    geography = (version.geographic_scope or version.factor.country or "").lower()
    geography_score = 10 if "colombia" in geography else 7 if geography in {"global", "internacional"} else 4
    status_score = 10 if version.status == "Aprobado" else 0
    documentation = session.scalar(select(FactorDocumentation).where(FactorDocumentation.factor_version_id == version.id))
    reference_year = documentation.data_year if documentation and documentation.data_year else version.publication_year
    temporal_gap = abs(record.period_start.year - int(reference_year or record.period_start.year))
    temporal_score = 8 if temporal_gap <= 1 else 5 if temporal_gap <= 3 else 2
    if documentation and documentation.source_document_id and documentation.review_status in {"Aprobado documentalmente", "Aprobado"}:
        documentation_score = 5
    elif documentation:
        documentation_score = 3
    else:
        documentation_score = 1 if version.source_document else 0
    score = min(100, unit_score + semantic_score + geography_score + status_score + temporal_score + documentation_score)
    # Un factor demostrativo puede ser matemáticamente compatible, pero no debe
    # ocupar los primeros lugares de una decisión metodológica formal.
    if documentation and documentation.reporting_use == "Demostrativo":
        score = min(score, 40)
    elif documentation and documentation.reporting_use == "Retirado":
        score = 0
    reasons = [unit_note]
    reasons.append("Coincidencias operativas: " + ", ".join(overlap) + "." if overlap else "No se detectaron coincidencias suficientes entre la fuente y el uso declarado del factor.")
    reasons.append(f"Representatividad geográfica: {version.geographic_scope or version.factor.country or 'sin definir'}.")
    reasons.append(f"Referencia temporal: año {reference_year}; dato del año {record.period_start.year}.")
    if version.technology_scope:
        reasons.append(f"Cobertura tecnológica: {version.technology_scope}.")
    if documentation:
        reasons.append(f"Aptitud documental: {documentation.reporting_use}, calidad {documentation.quality_grade}, revisión {documentation.review_status}.")
    else:
        reasons.append("No existe una ficha documental estructurada para esta versión.")
    blockers: list[str] = []
    if not calculable:
        blockers.append("No existe una conversión aprobada entre las unidades.")
    if semantic_score < 7:
        blockers.append("La relación entre la actividad y el factor requiere justificación adicional.")
    if temporal_score <= 2:
        blockers.append("La representatividad temporal es baja.")
    if version.effective_from and record.period_start < version.effective_from:
        blockers.append("El dato es anterior al inicio de vigencia declarado para el factor.")
    if version.effective_to and record.period_start > version.effective_to:
        blockers.append("El dato es posterior al fin de vigencia declarado para el factor.")
    if version.status != "Aprobado":
        blockers.append("La versión del factor no está aprobada.")
    if documentation:
        if documentation.reporting_use == "Demostrativo":
            blockers.append("El factor está clasificado para uso exclusivamente demostrativo.")
        if documentation.reporting_use == "Retirado":
            blockers.append("El factor está retirado para nuevos usos.")
        if documentation.review_status not in {"Aprobado documentalmente", "Aprobado", "Demostrativo"}:
            blockers.append(f"La revisión documental permanece en estado {documentation.review_status}.")
        if documentation.next_review_date and documentation.next_review_date < date.today():
            blockers.append("La revisión documental del factor está vencida.")
    hard_blockers = [item for item in blockers if any(token in item.lower() for token in ["no existe una conversión", "demostrativo", "retirado", "no está aprobada", "fuera de vigencia", "anterior al inicio", "posterior al fin"])]
    recommendation = "Recomendado" if score >= 78 and calculable and not hard_blockers else "Revisar" if score >= 55 and calculable and not hard_blockers else "No recomendado"
    return {
        "version": version,
        "score": score,
        "recommendation": recommendation,
        "calculable": calculable,
        "reasons": reasons,
        "blockers": blockers,
        "hard_blockers": hard_blockers,
        "unit_note": unit_note,
        "overlap": overlap,
        "documentation": documentation,
        "breakdown": {
            "units": unit_score,
            "activity": semantic_score,
            "geography": geography_score,
            "approval": status_score,
            "time": temporal_score,
            "documentation": documentation_score,
        },
    }


def conversation_for_record(session: Session, source: EmissionSource, record: ActivityData, versions: list[EmissionFactorVersion], limit: int = 6) -> dict[str, object]:
    candidates = [advise_factor(session, source, record, version) for version in versions]
    candidates.sort(key=lambda item: (bool(item["calculable"]), int(item["score"])), reverse=True)
    selections = [item for item in getattr(record, "factor_selections", []) if item.active]
    selected_ids = {item.factor_version_id for item in selections}
    applied = [item for item in selections if item.selection_status in APPLIED_SELECTION_STATUSES]
    pending = [item for item in selections if item.selection_status in PENDING_SELECTION_STATUSES]
    warnings: list[str] = []
    if pending:
        warnings.append(f"{len(pending)} selección(es) requieren revisión antes de aplicarse al cálculo.")
    if len(applied) > 1:
        gases = [getattr(getattr(item.factor_version, "gas", None), "code", "") for item in applied]
        repeated = sorted({gas for gas in gases if gas and gases.count(gas) > 1})
        if repeated:
            warnings.append("Posible doble conteo: hay más de un factor aprobado para " + ", ".join(repeated) + ".")
    low_fit = [item for item in applied if item.compatibility_score < 70]
    if low_fit:
        warnings.append("Existe una selección aplicada con compatibilidad inferior a 70%; documenta la excepción.")
    if applied:
        control_status = "Aprobado con alertas" if warnings else "Aprobado"
        selection_mode = "Específico del dato"
    elif pending:
        control_status = "Pendiente de revisión"
        selection_mode = "Propuesta específica sin aplicar"
    else:
        control_status = "Herencia controlada"
        selection_mode = "Hereda factores de la fuente"
    return {
        "record": record,
        "candidates": candidates[:limit],
        "selected_ids": selected_ids,
        "applied_ids": {item.factor_version_id for item in applied},
        "selections": selections,
        "pending": pending,
        "applied": applied,
        "selection_mode": selection_mode,
        "control_status": control_status,
        "warnings": warnings,
        "questions": [
            "¿La unidad del dato puede convertirse de forma aprobada a la unidad del factor?",
            "¿El factor representa el material, proceso, tecnología y geografía reales?",
            "¿El año y la fuente documental son suficientemente representativos?",
            "¿Se requiere más de un factor para desagregar gases o componentes del dato?",
            "¿La combinación evita doble conteo y conserva una justificación reproducible?",
        ],
    }
