from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any


FREQUENCY_MONTHS = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "semestral": 6,
    "anual": 12,
}


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def period_end(start: date, months: int, inventory_end: date) -> date:
    candidate = add_months(start, months)
    candidate = date(candidate.year, candidate.month, 1)
    end = candidate.fromordinal(candidate.toordinal() - 1)
    return min(end, inventory_end)


def expected_periods(inventory: Any, source: Any) -> list[tuple[date, date]]:
    frequency = str(getattr(source, "data_frequency", "Mensual") or "Mensual").strip().casefold()
    step = FREQUENCY_MONTHS.get(frequency)
    if not step:
        return [(inventory.start_date, inventory.end_date)]
    periods: list[tuple[date, date]] = []
    current = inventory.start_date
    while current <= inventory.end_date:
        end = period_end(current, step, inventory.end_date)
        periods.append((current, end))
        current = add_months(date(current.year, current.month, 1), step)
    return periods


def _contains_record(records: list[Any], start: date, end: date) -> bool:
    return any(item.period_start <= end and item.period_end >= start for item in records)


def evidence_profile(source: Any) -> dict[str, str]:
    text = f"{getattr(source, 'name', '')} {getattr(source, 'category', '')}".casefold()
    profiles = (
        (("electric", "energía adquirida", "scope 2"), "Factura o lectura del medidor", "Factura", "kWh", "Concilia el periodo facturado con la sede y conserva el soporte completo."),
        (("combust", "diésel", "diesel", "gasolina", "gas natural", "glp"), "Factura, vale o registro de abastecimiento", "Factura", "L", "Confirma tipo de combustible, unidad, equipo o vehículo y periodo de consumo."),
        (("papel", "cartón", "carton"), "Factura o registro de compras por tipo de material", "Registro contable", "kg", "Diferencia tipo de papel, contenido reciclado y uso cuando la evidencia lo permita."),
        (("residuo", "disposición", "disposicion", "tratamiento", "compost", "relleno"), "Pesaje, certificado de tratamiento o disposición", "Certificado", "t", "Separa material recibido, aprovechado, tratado y rechazado para evitar dobles conteos."),
        (("transporte", "viaje", "movilidad", "vuelo", "carga"), "Planilla, factura, manifiesto o reporte de viajes", "Registro operativo", "km", "Conserva distancia, modo, carga o pasajeros y condición propia o contratada."),
        (("fertiliz", "enmienda", "nitrógeno", "nitrogeno"), "Factura y registro de aplicación por lote o cultivo", "Registro operativo", "kg", "Registra composición, cantidad aplicada, área, cultivo y periodo; no mezcles compra con aplicación."),
        (("estiércol", "estiercol", "ganado", "fermentación", "fermentacion"), "Censo animal y registro productivo", "Registro operativo", "unidad", "Diferencia especie, categoría animal, sistema productivo y manejo del estiércol."),
        (("refriger", "fuga", "gas refrigerante"), "Orden de mantenimiento y recarga de refrigerante", "Registro operativo", "kg", "Identifica gas, cantidad recargada o recuperada y equipo intervenido."),
        (("agua", "vertimiento"), "Factura, lectura de medidor o balance operativo", "Medición directa", "m³", "Alinea lectura, sede, periodo y tratamiento cuando aplique."),
    )
    for keywords, evidence, origin, fallback_unit, note in profiles:
        if any(keyword in text for keyword in keywords):
            return {
                "evidence": evidence,
                "origin": origin,
                "unit": getattr(source, "preferred_unit", "") or fallback_unit,
                "note": note,
            }
    return {
        "evidence": "Registro verificable, factura, certificado o medición",
        "origin": "Registro operativo",
        "unit": getattr(source, "preferred_unit", "") or "unidad",
        "note": "Confirma que el dato corresponde al límite, periodo y unidad del inventario antes de guardarlo.",
    }


def source_capture_card(inventory: Any, source: Any) -> dict[str, Any]:
    records = sorted(list(getattr(source, "activity_records", []) or []), key=lambda item: (item.period_start, item.id))
    periods = expected_periods(inventory, source)
    complete = sum(1 for start, end in periods if _contains_record(records, start, end))
    missing = [(start, end) for start, end in periods if not _contains_record(records, start, end)]
    latest = records[-1] if records else None
    next_period = missing[0] if missing else None
    support_count = sum(1 for item in records if getattr(item, "evidence_id", None))
    approved_count = sum(1 for item in records if getattr(item, "status", "") == "Aprobado")
    expected_count = max(len(periods), 1)
    coverage = round((complete / expected_count) * 100)
    support_coverage = round((support_count / len(records)) * 100) if records else 0
    profile = evidence_profile(source)
    if not records:
        status = "Sin iniciar"
        tone = "pending"
    elif missing:
        status = "Pendiente"
        tone = "progressing"
    elif support_count < len(records):
        status = "Revisar soportes"
        tone = "warning"
    else:
        status = "Al día"
        tone = "complete"
    priority_score = 0
    if str(getattr(source, "materiality", "")).casefold() == "alta":
        priority_score += 3
    if not records:
        priority_score += 3
    elif missing:
        priority_score += 2
    if support_count < len(records):
        priority_score += 1
    return {
        "source": source,
        "profile": profile,
        "records": records,
        "latest": latest,
        "expected_count": expected_count,
        "complete_count": complete,
        "missing_count": len(missing),
        "coverage": coverage,
        "support_coverage": support_coverage,
        "approved_count": approved_count,
        "status": status,
        "tone": tone,
        "priority_score": priority_score,
        "next_start": next_period[0] if next_period else None,
        "next_end": next_period[1] if next_period else None,
    }


def capture_summary(inventory: Any) -> dict[str, Any]:
    cards = [source_capture_card(inventory, source) for source in inventory.sources if source.included]
    cards.sort(key=lambda item: (-item["priority_score"], item["source"].scope, item["source"].name.casefold()))
    expected = sum(item["expected_count"] for item in cards)
    complete = sum(item["complete_count"] for item in cards)
    total_records = sum(len(item["records"]) for item in cards)
    supported = sum(sum(1 for record in item["records"] if record.evidence_id) for item in cards)
    return {
        "cards": cards,
        "sources": len(cards),
        "sources_ready": sum(1 for item in cards if item["status"] == "Al día"),
        "pending_sources": sum(1 for item in cards if item["status"] != "Al día"),
        "expected_periods": expected,
        "complete_periods": complete,
        "coverage": round((complete / expected) * 100) if expected else 0,
        "support_coverage": round((supported / total_records) * 100) if total_records else 0,
        "next_action": next((item for item in cards if item["status"] != "Al día"), cards[0] if cards else None),
    }
