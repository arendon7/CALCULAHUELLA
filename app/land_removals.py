from __future__ import annotations

from collections import defaultdict
from math import isfinite

ENTRY_TYPES = (
    "Emisión de cambio de uso de suelo",
    "Emisión de manejo de tierras",
    "CO2 biogénico emitido",
    "Remoción de CO2",
    "Pérdida o reversión de carbono almacenado",
    "Carbono almacenado en producto",
    "Emisión evitada / beneficio circular",
)
LAND_CATEGORIES = (
    "Tierras agrícolas", "Pastizales productivos", "Agroforestería", "Silvopastoreo",
    "Humedales productivos", "Infraestructura de remoción tecnológica", "Producto biogénico", "No aplica",
)
CARBON_POOLS = (
    "Biomasa aérea", "Biomasa subterránea", "Carbono orgánico del suelo", "Madera muerta",
    "Hojarasca", "Producto", "Reservorio geológico", "No aplica",
)
TRACEABILITY_LEVELS = ("Predio específico", "Proveedor específico", "Región subnacional", "País de origen", "Desconocido")
SCOPES = ("Alcance 1", "Alcance 2", "Alcance 3", "Fuera de alcances")


def validate_entry(payload: dict) -> list[str]:
    errors: list[str] = []
    entry_type = str(payload.get("entry_type", ""))
    quantity = float(payload.get("quantity_tco2e") or 0)
    uncertainty = float(payload.get("uncertainty_percentage") or 0)
    storage = int(payload.get("storage_duration_years") or 0)
    if entry_type not in ENTRY_TYPES:
        errors.append("Tipo de partida no reconocido.")
    if not isfinite(quantity) or quantity <= 0:
        errors.append("La cantidad debe ser positiva y finita.")
    if not 0 <= uncertainty <= 100:
        errors.append("La incertidumbre debe estar entre 0 % y 100 %.")
    if payload.get("end_date") and payload.get("start_date") and payload["end_date"] < payload["start_date"]:
        errors.append("La fecha final no puede ser anterior a la inicial.")
    if not str(payload.get("methodology", "")).strip():
        errors.append("Debe documentarse la metodología.")
    if not str(payload.get("source_reference", "")).strip():
        errors.append("Debe indicarse una fuente o referencia verificable.")
    if entry_type == "Remoción de CO2":
        if storage <= 0:
            errors.append("La remoción requiere duración esperada del almacenamiento.")
        if not payload.get("reversal_monitoring"):
            errors.append("La remoción requiere monitoreo de reversión o pérdida.")
        if not payload.get("lifecycle_complete"):
            errors.append("La remoción requiere contabilizar emisiones del ciclo de vida.")
    if entry_type == "Carbono almacenado en producto" and storage <= 0:
        errors.append("El almacenamiento en producto requiere una duración estimada.")
    if entry_type == "Emisión evitada / beneficio circular" and str(payload.get("reporting_scope")) != "Fuera de alcances":
        errors.append("Las emisiones evitadas deben reportarse fuera de los alcances y no netear el inventario.")
    if entry_type == "CO2 biogénico emitido" and str(payload.get("gas", "CO2")).upper() != "CO2":
        errors.append("La partida informativa biogénica debe usar CO2; CH4 y N2O se contabilizan en los alcances.")
    return errors


def land_summary(entries) -> dict:
    totals = defaultdict(float)
    by_land = defaultdict(float)
    warnings: list[str] = []
    for item in entries:
        totals[item.entry_type] += float(item.quantity_tco2e or 0)
        by_land[item.land_category] += float(item.quantity_tco2e or 0)
        if item.status == "Aprobado" and not item.verified:
            warnings.append(f"{item.activity_name}: aprobado sin verificación independiente.")
        if item.traceability_level in {"País de origen", "Desconocido"} and item.entry_type == "Remoción de CO2":
            warnings.append(f"{item.activity_name}: trazabilidad insuficiente para una remoción robusta.")
        if item.uncertainty_percentage > 30:
            warnings.append(f"{item.activity_name}: incertidumbre superior al 30 %.")
    gross_land = totals["Emisión de cambio de uso de suelo"] + totals["Emisión de manejo de tierras"]
    return {
        "totals": dict(totals),
        "by_land": dict(sorted(by_land.items())),
        "gross_land_emissions": round(gross_land, 6),
        "biogenic_memo": round(totals["CO2 biogénico emitido"], 6),
        "removals": round(totals["Remoción de CO2"], 6),
        "reversals": round(totals["Pérdida o reversión de carbono almacenado"], 6),
        "product_storage": round(totals["Carbono almacenado en producto"], 6),
        "avoided": round(totals["Emisión evitada / beneficio circular"], 6),
        "approved": sum(1 for item in entries if item.status == "Aprobado"),
        "pending": sum(1 for item in entries if item.status != "Aprobado"),
        "warnings": list(dict.fromkeys(warnings)),
        "entry_count": len(entries),
    }
