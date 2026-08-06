from __future__ import annotations

"""Consulting-grade narrative layer for controlled carbon reports.

The module interprets already calculated and reviewed information. It never
changes activity data, factors, GWP values, formulas or persisted results.
"""

from typing import Any

from sqlalchemy.orm import Session

from .analytics import full_analysis, indicator_metrics
from .database import Inventory
from .delivery_readiness import professional_delivery_summary
from .methodology_closure import closure_summary
from .reduction_portfolio import portfolio_summary

READY = "Listo"
PROGRESS = "En progreso"
BLOCKED = "Bloqueado"


def _change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 1)


def _direction(value: float | None) -> str:
    if value is None:
        return "Sin comparación"
    if abs(value) < 0.05:
        return "Estable"
    return "Aumentó" if value > 0 else "Disminuyó"


def _status(score: float, blocked: bool = False) -> str:
    if blocked:
        return BLOCKED
    if score >= 85:
        return READY
    return PROGRESS


def _intensity_metrics(session: Session, inventory: Inventory, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    previous_info = analysis["history"].get("previous")
    previous_inventory = session.get(Inventory, previous_info["inventory_id"]) if previous_info else None
    previous_indicators = indicator_metrics(session, previous_inventory.id) if previous_inventory else {}
    previous_total = float(previous_info["total"]) if previous_info else None

    specs = [
        ("Producción", "intensity_production", "tCO2e por unidad producida", "Desempeño operativo"),
        ("Empleados", "intensity_employee", "tCO2e por empleado", "Escala organizacional"),
        ("Ingresos", "intensity_revenue", "tCO2e por millón COP", "Eficiencia económica"),
    ]
    result: list[dict[str, Any]] = []
    current_indicators = analysis["indicators"]
    for indicator_name, key, unit, interpretation in specs:
        current_value = analysis.get(key)
        previous_indicator = previous_indicators.get(indicator_name)
        previous_value = None
        if previous_total is not None and previous_indicator and previous_indicator.value:
            denominator = previous_indicator.value / 1_000_000 if indicator_name == "Ingresos" else previous_indicator.value
            previous_value = previous_total / denominator if denominator else None
        change = _change(float(current_value) if current_value is not None else None, previous_value)
        indicator = current_indicators.get(indicator_name)
        result.append({
            "name": indicator_name,
            "value": round(float(current_value), 6) if current_value is not None else None,
            "previous_value": round(float(previous_value), 6) if previous_value is not None else None,
            "change": change,
            "direction": _direction(change),
            "unit": unit,
            "denominator": round(float(indicator.value), 3) if indicator else None,
            "denominator_unit": indicator.unit if indicator else "",
            "interpretation": interpretation,
            "available": current_value is not None,
        })
    return result


def consulting_report_summary(
    session: Session,
    inventory: Inventory,
    *,
    analysis: dict[str, Any] | None = None,
    delivery: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analysis = analysis or full_analysis(session, inventory)
    closure = closure or closure_summary(session, inventory)
    delivery = delivery or professional_delivery_summary(session, inventory, analysis=analysis, closure=closure)
    portfolio = portfolio or portfolio_summary(session, inventory)

    total = float(analysis["total"] or 0)
    quality = analysis["quality"]
    history = analysis["history"]
    sources = list(analysis["sources_summary"])
    intensities = _intensity_metrics(session, inventory, analysis)
    previous = history.get("previous")
    total_change = history.get("total_change")
    intensity_change = history.get("intensity_change")
    top_three_share = round(sum(float(item["share"]) for item in sources[:3]), 1)

    comparison = {
        "available": previous is not None,
        "previous_year": previous["year"] if previous else None,
        "previous_total": float(previous["total"]) if previous else None,
        "current_total": total,
        "absolute_change": total_change,
        "absolute_direction": _direction(total_change),
        "production_intensity_change": intensity_change,
        "production_intensity_direction": _direction(intensity_change),
        "warning": (
            "La comparación debe interpretarse junto con cambios de límites, metodología, producción y calidad del dato."
            if previous else
            "No existe un periodo anterior comparable dentro de la organización."
        ),
    }

    findings: list[dict[str, Any]] = []
    if total <= 0:
        findings.append({
            "level": "Crítica", "topic": "Resultado", "finding": "El inventario no tiene emisiones calculadas.",
            "evidence": "Total reportado igual a 0 tCO2e.",
            "implication": "No es posible formular conclusiones de desempeño.",
            "recommendation": "Completar datos, factores y cálculo antes de emitir el informe.",
        })
    if sources:
        top = sources[0]
        findings.append({
            "level": "Alta" if float(top["share"]) >= 40 else "Media",
            "topic": "Materialidad",
            "finding": f"{top['name']} es la fuente de mayor contribución.",
            "evidence": f"Representa {top['share']:.1f}% del total ({top['emissions']:.2f} tCO2e).",
            "implication": "La primera decisión de reducción y mejora de datos debe concentrarse en esta fuente.",
            "recommendation": f"Validar responsable, palanca técnica, costo y fecha para intervenir {top['name']}.",
        })
    if top_three_share >= 70:
        findings.append({
            "level": "Alta", "topic": "Concentración",
            "finding": "La huella está concentrada en pocas fuentes.",
            "evidence": f"Las tres principales fuentes explican {top_three_share:.1f}% del inventario.",
            "implication": "Un portafolio focalizado puede capturar una proporción material del potencial de reducción.",
            "recommendation": "Priorizar las tres fuentes dominantes antes de dispersar recursos en medidas marginales.",
        })
    if total_change is not None:
        findings.append({
            "level": "Alta" if abs(float(total_change)) >= 10 else "Media",
            "topic": "Evolución",
            "finding": f"La huella absoluta {_direction(total_change).lower()} frente al periodo anterior.",
            "evidence": f"Variación interanual de {total_change:+.1f}%.",
            "implication": "La variación debe explicarse por actividad, límites, factores y acciones ejecutadas.",
            "recommendation": "Documentar los principales controladores del cambio y separar efecto de actividad de efecto de eficiencia.",
        })
    if quality["evidence_coverage"] < 80:
        findings.append({
            "level": "Alta", "topic": "Trazabilidad",
            "finding": "La cobertura documental está por debajo del umbral operativo.",
            "evidence": f"{quality['evidence_coverage']}% de los registros cuenta con evidencia.",
            "implication": "Reduce la confianza del resultado y limita su uso externo.",
            "recommendation": "Cerrar soportes de las fuentes materiales hasta alcanzar al menos 80% de cobertura.",
        })
    if quality["estimated_share"] > 20:
        findings.append({
            "level": "Media", "topic": "Estimaciones",
            "finding": "Existe una participación relevante de datos estimados.",
            "evidence": f"{quality['estimated_share']}% de los registros fue marcado como estimado.",
            "implication": "La incertidumbre puede estar dominada por supuestos y no por medición directa.",
            "recommendation": "Sustituir primero las estimaciones asociadas a las fuentes de mayor contribución.",
        })
    if portfolio["actions"]:
        findings.append({
            "level": "Media", "topic": "Reducción",
            "finding": f"El portafolio de reducción presenta el estado: {portfolio['portfolio_status'].lower()}.",
            "evidence": f"Cobertura de meta {portfolio['coverage_percent']:.1f}% y preparación {portfolio['readiness_score']}%.",
            "implication": "La capacidad de convertir el inventario en gestión depende del cierre de responsables, recursos y fechas.",
            "recommendation": portfolio["primary_decision"],
        })
    else:
        findings.append({
            "level": "Alta", "topic": "Reducción", "finding": "No existe un portafolio formal de reducción.",
            "evidence": "No se registran acciones asociadas al inventario.",
            "implication": "El inventario aún no se traduce en una agenda de gestión climática.",
            "recommendation": "Crear acciones con fuente, responsable, inversión, ahorro, reducción y fecha objetivo.",
        })

    limitations: list[dict[str, str]] = []
    if not comparison["available"]:
        limitations.append({"category": "Comparabilidad", "detail": comparison["warning"]})
    if quality["evidence_coverage"] < 100:
        limitations.append({"category": "Evidencia", "detail": f"La cobertura documental es {quality['evidence_coverage']}%, no 100%."})
    if quality["estimated_share"]:
        limitations.append({"category": "Datos", "detail": f"El {quality['estimated_share']}% de los registros está identificado como estimado."})
    if not closure["uncertainty"]["complete"]:
        limitations.append({"category": "Incertidumbre", "detail": "La incertidumbre no está completa para todas las fuentes materiales."})
    if inventory.status not in {"Aprobado", "Cerrado"}:
        limitations.append({"category": "Gobierno", "detail": "El inventario no tiene aprobación o cierre formal."})
    limitations.append({"category": "Aseguramiento", "detail": "La revisión interna de la plataforma no equivale a verificación independiente."})

    recommendations: list[dict[str, str]] = []
    for finding in findings:
        recommendations.append({
            "priority": finding["level"], "topic": finding["topic"], "action": finding["recommendation"],
            "owner": (
                "Dirección y responsable climático" if finding["topic"] in {"Materialidad", "Concentración", "Reducción"}
                else "Consultor metodológico" if finding["topic"] in {"Evolución", "Estimaciones"}
                else "Responsable de información"
            ),
            "acceptance": (
                "Decisión registrada con responsable, fecha y evidencia de cierre."
                if finding["level"] == "Alta" else "Acción incorporada al plan de mejora del siguiente periodo."
            ),
        })

    chapters = [
        {"code": "context", "name": "Contexto, objetivo y límites", "score": 100 if inventory.objective and inventory.methodology else 60, "blocked": False},
        {"code": "results", "name": "Resultados y materialidad", "score": 100 if total > 0 and sources else 0, "blocked": total <= 0},
        {"code": "comparison", "name": "Comparación entre periodos", "score": 100 if comparison["available"] else 50, "blocked": False},
        {"code": "intensity", "name": "Indicadores de intensidad", "score": round(sum(100 for item in intensities if item["available"]) / max(len(intensities), 1)), "blocked": False},
        {"code": "quality", "name": "Calidad, evidencia e incertidumbre", "score": round((quality["score"] + quality["evidence_coverage"] + closure["uncertainty"]["emission_coverage_percentage"]) / 3), "blocked": False},
        {"code": "reduction", "name": "Recomendaciones y reducción", "score": portfolio["readiness_score"] if portfolio["actions"] else 25, "blocked": False},
        {"code": "publication", "name": "Control de publicación", "score": 100 if delivery["release_ready"] else delivery["score"], "blocked": delivery["publication"]["code"] == "internal"},
    ]
    for chapter in chapters:
        chapter["status"] = _status(float(chapter["score"]), bool(chapter["blocked"]))
        chapter["action"] = {
            "context": "Confirmar objetivo, límites y metodología.",
            "results": "Completar el cálculo y la clasificación de fuentes.",
            "comparison": "Crear o validar un periodo base comparable.",
            "intensity": "Registrar producción, empleados e ingresos cuando sean pertinentes.",
            "quality": "Cerrar evidencia e incertidumbre de fuentes materiales.",
            "reduction": "Estructurar medidas con economía, responsable y fecha.",
            "publication": "Cerrar puertas de entrega y aprobación formal.",
        }[chapter["code"]]

    report_score = round(sum(float(item["score"]) for item in chapters) / len(chapters))
    claims = [
        {"label": "Inventario cuantificado", "allowed": total > 0, "guidance": "Puede comunicarse con periodo, límites, metodología y limitaciones."},
        {"label": "Inventario final", "allowed": delivery["release_ready"], "guidance": "Solo cuando las puertas críticas y la aprobación estén cerradas."},
        {"label": "Inventario verificado", "allowed": False, "guidance": "Requiere una declaración independiente de verificación; la plataforma no la presume."},
        {"label": "Carbono neutral", "allowed": False, "guidance": "Requiere reglas, reducciones, remociones o compensaciones y aseguramiento adicionales."},
    ]

    return {
        "version": "1.0.0",
        "report_score": report_score,
        "status": "Listo para edición" if report_score >= 80 else "Requiere completar capítulos",
        "audience": "Dirección, equipo técnico, clientes y revisores autorizados",
        "purpose": "Explicar el resultado, sus causas, calidad, limitaciones y decisiones recomendadas sin sobreafirmar el nivel de aseguramiento.",
        "comparison": comparison,
        "intensities": intensities,
        "findings": findings,
        "limitations": limitations,
        "recommendations": recommendations,
        "chapters": chapters,
        "claims": claims,
        "top_three_share": top_three_share,
        "editorial_outline": [
            "Resumen ejecutivo", "Perfil y objetivo", "Límites y metodología", "Resultados", "Comparación e intensidades",
            "Calidad e incertidumbre", "Hallazgos", "Plan de reducción", "Limitaciones", "Anexos metodológicos",
        ],
        "analysis": analysis,
        "delivery": delivery,
        "closure": closure,
        "portfolio": portfolio,
    }
