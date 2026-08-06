from __future__ import annotations

"""Professional-delivery readiness and decision control for an inventory.

The module does not alter calculations, emission factors or persisted
methodology. It aggregates existing records into an explainable closure,
publication and decision view.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .analytics import full_analysis
from .database import ActivityData, EmissionCalculation, EmissionSource, Inventory
from .methodology_closure import closure_summary
from .reduction_portfolio import portfolio_summary

READY = "Listo"
PROGRESS = "En progreso"
BLOCKED = "Bloqueado"


def _number_es(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _gate(
    code: str,
    name: str,
    status: str,
    detail: str,
    action: str,
    href: str,
    *,
    owner: str,
    acceptance: str,
    critical: bool = False,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "status": status,
        "detail": detail,
        "action": action,
        "href": href,
        "owner": owner,
        "acceptance": acceptance,
        "critical": critical,
        "weight": 2 if critical else 1,
        "score": 100 if status == READY else 50 if status == PROGRESS else 0,
    }


def _approved_factor(source: EmissionSource) -> bool:
    if source.category == "Datos específicos de proveedores":
        return True
    return any(
        assignment.active and assignment.factor_version.status == "Aprobado"
        for assignment in source.factor_assignments
    )


def _action_plan(gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status_order = {BLOCKED: 0, PROGRESS: 1, READY: 2}
    pending = [gate for gate in gates if gate["status"] != READY]
    pending.sort(key=lambda gate: (status_order[gate["status"]], not gate["critical"], gate["code"]))
    plan: list[dict[str, Any]] = []
    for index, gate in enumerate(pending, start=1):
        if gate["status"] == BLOCKED and gate["critical"]:
            priority = "Crítica"
        elif gate["status"] == BLOCKED or gate["critical"]:
            priority = "Alta"
        else:
            priority = "Media"
        plan.append(
            {
                "number": index,
                "code": gate["code"],
                "title": gate["action"],
                "stage": gate["name"],
                "priority": priority,
                "owner": gate["owner"],
                "detail": gate["detail"],
                "acceptance": gate["acceptance"],
                "href": gate["href"],
            }
        )
    return plan


def _publication_control(
    inventory: Inventory,
    *,
    total: float,
    score: int,
    release_ready: bool,
    critical_pending: list[dict[str, Any]],
) -> dict[str, Any]:
    if total <= 0 or any(item["status"] == BLOCKED for item in critical_pending):
        return {
            "code": "internal",
            "level": "Uso interno",
            "tone": "blocked",
            "can_share_external": False,
            "audience": "Equipo técnico y responsables de información",
            "message": "No debe comunicarse externamente: faltan resultados o controles críticos del inventario.",
            "notice": "Resultado preliminar sujeto a completar datos, factores, revisión y aprobación.",
        }
    if not inventory.status in {"Aprobado", "Cerrado"}:
        return {
            "code": "draft",
            "level": "Borrador técnico controlado",
            "tone": "warning",
            "can_share_external": False,
            "audience": "Dirección y equipo técnico interno",
            "message": "Puede apoyar revisión interna, pero no debe presentarse como inventario final ni verificado.",
            "notice": "Documento de trabajo no aprobado. No constituye verificación independiente.",
        }
    if critical_pending or score < 85:
        return {
            "code": "review",
            "level": "Revisión dirigida",
            "tone": "warning",
            "can_share_external": False,
            "audience": "Aprobador, revisor y dirección",
            "message": "Existe aprobación formal, pero permanecen controles que deben cerrarse antes de la entrega externa.",
            "notice": "Versión aprobada con condiciones pendientes de cierre documental o metodológico.",
        }
    if release_ready:
        return {
            "code": "final",
            "level": "Versión final controlada",
            "tone": "ready",
            "can_share_external": True,
            "audience": "Dirección, clientes, financiadores y revisores autorizados",
            "message": "Puede compartirse de forma controlada junto con sus limitaciones, versión y expediente de soporte.",
            "notice": "Inventario aprobado. La revisión interna no equivale a verificación independiente.",
        }
    return {
        "code": "draft",
        "level": "Borrador técnico controlado",
        "tone": "warning",
        "can_share_external": False,
        "audience": "Dirección y equipo técnico interno",
        "message": "El inventario requiere cierre adicional antes de una comunicación externa.",
        "notice": "Documento de trabajo sujeto a revisión y aprobación.",
    }


def _decision_brief(
    analysis: dict[str, Any],
    closure: dict[str, Any],
    publication: dict[str, Any],
) -> dict[str, Any]:
    total = float(analysis["total"] or 0)
    sources = list(analysis["sources_summary"])
    quality = analysis["quality"]
    reduction = analysis["reduction"]
    uncertainty = closure["uncertainty"]
    top = sources[0] if sources else None
    top_three_share = round(sum(float(item["share"]) for item in sources[:3]), 1)
    reduction_percentage = round(float(reduction["expected_reduction"] or 0) / total * 100, 1) if total else 0

    if total <= 0:
        primary_decision = "Completar la cuantificación antes de definir metas, inversiones o compromisos externos."
    elif quality["score"] < 60:
        primary_decision = "Priorizar la calidad y trazabilidad del dato antes de usar el resultado para decisiones externas."
    elif top and float(top["share"]) >= 50:
        primary_decision = f"Concentrar la primera ola de reducción en {top['name']}, principal foco del inventario."
    elif reduction["actions"]:
        primary_decision = "Aprobar responsables, recursos y fechas del portafolio de reducción para convertir el inventario en gestión."
    else:
        primary_decision = "Formalizar un plan de reducción conectado con las fuentes de mayor contribución."

    recommendations: list[str] = []
    if top:
        recommendations.append(
            f"Validar un caso de intervención sobre {top['name']} ({top['share']:.1f}% del total)."
        )
    if quality["evidence_coverage"] < 80:
        recommendations.append(
            f"Elevar la cobertura documental de {quality['evidence_coverage']}% al umbral operativo mínimo de 80%."
        )
    if quality["estimated_share"] > 20:
        recommendations.append(
            f"Sustituir datos estimados prioritarios; actualmente representan {quality['estimated_share']}% de los registros."
        )
    if not uncertainty["complete"]:
        recommendations.append("Completar la incertidumbre de las fuentes materiales antes del cierre técnico.")
    if not reduction["actions"]:
        recommendations.append("Crear acciones de reducción con responsable, fecha, costo y reducción esperada.")
    if not recommendations:
        recommendations.append("Mantener el control de versión y preparar el expediente para revisión o verificación externa.")

    confidence_score = round(
        quality["score"] * 0.45
        + quality["evidence_coverage"] * 0.35
        + (100 if uncertainty["complete"] else float(uncertainty["emission_coverage_percentage"] or 0)) * 0.20
    )
    confidence_label = "Alta" if confidence_score >= 80 else "Media" if confidence_score >= 60 else "Baja"

    return {
        "primary_decision": primary_decision,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "top_source": top,
        "top_three_share": top_three_share,
        "reduction_percentage": reduction_percentage,
        "recommendations": recommendations[:5],
        "questions": [
            "¿Qué fuente debe intervenirse primero y quién tiene autoridad para hacerlo?",
            "¿Qué limitaciones deben comunicarse junto con el resultado?",
            "¿Qué controles faltan para pasar al nivel de publicación siguiente?",
        ],
        "share_message": publication["message"],
    }


def _executive_narrative(
    inventory: Inventory,
    analysis: dict[str, Any],
    closure: dict[str, Any],
    readiness_score: int,
) -> dict[str, Any]:
    total = float(analysis["total"] or 0)
    sources = list(analysis["sources_summary"])
    scopes = analysis["scopes"]
    quality = analysis["quality"]
    history = analysis["history"]
    reduction = analysis["reduction"]
    uncertainty = closure["uncertainty"]

    if total <= 0:
        headline = "El inventario todavía no cuenta con emisiones calculadas para sustentar una conclusión ejecutiva."
    else:
        leading_scope = max(scopes, key=lambda key: scopes[key]) if scopes else 1
        headline = (
            f"El inventario reporta {_number_es(total)} tCO₂e. El alcance {leading_scope} "
            f"concentra la mayor participación, con {_number_es(float(scopes.get(leading_scope, 0)))} tCO₂e."
        )

    findings: list[str] = []
    if sources and total > 0:
        top = sources[0]
        findings.append(f"La principal fuente es {top['name']}, con {top['share']:.1f}% del total reportado.")
        top_three_share = sum(float(item["share"]) for item in sources[:3])
        findings.append(f"Las tres fuentes de mayor contribución representan {top_three_share:.1f}% del inventario.")
    findings.append(
        f"La calidad consolidada es {quality['score']}% y la cobertura documental es {quality['evidence_coverage']}%."
    )
    if uncertainty["emission_coverage_percentage"]:
        findings.append(
            f"La incertidumbre combinada es {uncertainty['combined_percentage']:.2f}% sobre "
            f"{uncertainty['emission_coverage_percentage']:.1f}% de las emisiones brutas."
        )
    if history["total_change"] is not None:
        direction = "aumentó" if history["total_change"] > 0 else "disminuyó"
        findings.append(f"Frente al periodo anterior, la huella absoluta {direction} {abs(history['total_change']):.1f}%.")
    if reduction["actions"]:
        findings.append(
            f"El plan registra {len(reduction['actions'])} acción(es), con una reducción esperada de "
            f"{_number_es(float(reduction['expected_reduction']))} tCO₂e/año."
        )
    else:
        findings.append("Aún no se han formalizado acciones de reducción asociadas al inventario.")

    limitations: list[str] = []
    if quality["evidence_coverage"] < 80:
        limitations.append("La cobertura documental es inferior al umbral operativo de 80%.")
    if quality["estimated_share"] > 20:
        limitations.append(f"El {quality['estimated_share']}% de los registros corresponde a información estimada.")
    if not uncertainty["complete"]:
        limitations.append("La incertidumbre no está documentada de forma completa para todas las fuentes materiales.")
    if inventory.status not in {"Aprobado", "Cerrado"}:
        limitations.append("El inventario no cuenta todavía con aprobación o cierre formal.")
    if not limitations:
        limitations.append("No se identifican limitaciones operativas críticas en los registros disponibles.")

    conclusion = (
        f"La preparación integral para entrega es {readiness_score}%. "
        + (
            "El inventario puede pasar a aprobación y emisión controlada de entregables."
            if readiness_score >= 85 and inventory.status in {"Aprobado", "Cerrado"}
            else "Los resultados deben tratarse como borrador técnico hasta cerrar los controles pendientes."
        )
    )
    return {"headline": headline, "findings": findings, "limitations": limitations, "conclusion": conclusion}


def professional_delivery_summary(
    session: Session,
    inventory: Inventory,
    *,
    analysis: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analysis = analysis or full_analysis(session, inventory)
    closure = closure or closure_summary(session, inventory)
    reduction_portfolio = portfolio_summary(session, inventory)

    included = [source for source in inventory.sources if source.included]
    configured_sources = [
        source for source in included
        if source.name and source.category and source.scope in {1, 2, 3} and source.responsible
    ]
    covered_sources = [source for source in included if source.progress >= 100 and bool(source.activity_records)]
    missing_factors = [source for source in included if not _approved_factor(source)]
    open_observations = [item for item in inventory.observations if item.status != "Cerrada"]
    blocking_observations = [item for item in open_observations if item.severity in {"Mayor", "Crítica"}]
    error_count = int(
        session.scalar(
            select(func.count())
            .select_from(EmissionCalculation)
            .join(ActivityData)
            .join(EmissionSource)
            .where(
                EmissionSource.inventory_id == inventory.id,
                EmissionCalculation.status == "Error",
            )
        ) or 0
    )
    calculation_count = int(
        session.scalar(
            select(func.count())
            .select_from(EmissionCalculation)
            .join(ActivityData)
            .join(EmissionSource)
            .where(
                EmissionSource.inventory_id == inventory.id,
                EmissionCalculation.status == "Calculado",
            )
        ) or 0
    )

    config_ready = bool(
        inventory.objective
        and inventory.methodology
        and inventory.methodology_version
        and inventory.gwp_version
        and inventory.consolidation_approach
        and inventory.facility_links
    )
    source_ready = bool(included) and len(configured_sources) == len(included)
    coverage_ratio = round(100 * len(covered_sources) / max(len(included), 1))
    evidence_coverage = int(analysis["quality"]["evidence_coverage"])
    quality_score = int(analysis["quality"]["score"])
    factor_ready = not missing_factors and not error_count and calculation_count > 0
    methodology_score = int(closure["readiness_score"])
    review_ready = not blocking_observations and methodology_score >= 80
    reduction_ready = bool(reduction_portfolio["decision_ready"])
    reduction_started = int(reduction_portfolio["action_count"]) > 0
    approved = inventory.status in {"Aprobado", "Cerrado"}

    gates = [
        _gate(
            "profile", "Perfil, periodo y límites", READY if config_ready else BLOCKED,
            "Objetivo, metodología, GWP, consolidación y sedes están definidos."
            if config_ready else "Faltan elementos del perfil metodológico o de los límites organizacionales.",
            "Ver control de versión" if inventory.locked else "Completar configuración",
            "/control" if inventory.locked else f"/inventarios/{inventory.id}/editar",
            owner="Consultor metodológico", acceptance="Periodo, sedes, límites, estándar, versión y GWP documentados.", critical=True,
        ),
        _gate(
            "sources", "Fuentes materiales", READY if source_ready else (PROGRESS if included else BLOCKED),
            f"{len(configured_sources)} de {len(included)} fuentes incluidas tienen clasificación y responsable."
            if included else "El inventario no tiene fuentes incluidas.",
            "Revisar fuentes", f"/inventarios/{inventory.id}/fuentes",
            owner="Consultor y responsables de proceso", acceptance="Todas las fuentes incluidas tienen alcance, categoría, sede y responsable.", critical=True,
        ),
        _gate(
            "activity", "Cobertura de datos de actividad",
            READY if coverage_ratio == 100 and included else (PROGRESS if coverage_ratio > 0 else BLOCKED),
            f"{len(covered_sources)} de {len(included)} fuentes alcanzan cobertura completa ({coverage_ratio}%).",
            "Completar datos", "/captura-guiada",
            owner="Responsables de información", acceptance="Cada fuente material tiene registros completos para el periodo definido.", critical=True,
        ),
        _gate(
            "evidence", "Evidencias y trazabilidad",
            READY if evidence_coverage >= 80 else (PROGRESS if evidence_coverage > 0 else BLOCKED),
            f"La cobertura documental de los registros es {evidence_coverage}%.",
            "Vincular soportes", "/captura-guiada",
            owner="Responsables de información", acceptance="Cobertura documental mínima de 80% y soportes vinculados a los datos críticos.",
        ),
        _gate(
            "calculation", "Factores y cálculo reproducible",
            READY if factor_ready else (PROGRESS if calculation_count > 0 and not error_count else BLOCKED),
            f"{calculation_count} cálculo(s) válidos, sin factores faltantes ni errores."
            if factor_ready else f"Hay {len(missing_factors)} fuente(s) sin factor aprobado y {error_count} error(es); se conservan {calculation_count} cálculo(s) válidos.",
            "Revisar resultados calculados", "/calculos",
            owner="Consultor metodológico", acceptance="Factores aprobados, unidades compatibles, cero errores y cálculo reproducible.", critical=True,
        ),
        _gate(
            "quality", "Calidad e incertidumbre",
            READY if quality_score >= 80 and closure["uncertainty"]["complete"] else (PROGRESS if quality_score >= 60 else BLOCKED),
            f"Calidad consolidada: {quality_score}%. Preparación metodológica: {methodology_score}%.",
            "Revisar calidad", "/calidad-datos",
            owner="Consultor y revisor", acceptance="Calidad mínima de 80% e incertidumbre documentada en fuentes materiales.",
        ),
        _gate(
            "review", "Revisión profesional", READY if review_ready else (PROGRESS if not blocking_observations else BLOCKED),
            f"No existen hallazgos bloqueantes y el cierre metodológico alcanza {methodology_score}%."
            if review_ready else f"Hay {len(blocking_observations)} hallazgo(s) bloqueante(s) y {len(open_observations)} observación(es) abierta(s).",
            "Resolver revisión", "/control",
            owner="Revisor y aprobador", acceptance="Sin hallazgos mayores o críticos abiertos y decisión formal registrada.", critical=True,
        ),
        _gate(
            "delivery", "Reducción, aprobación y entrega",
            READY if reduction_ready and approved else (PROGRESS if reduction_started or approved else BLOCKED),
            (
                f"Portafolio listo para decisión: {reduction_portfolio['coverage_percent']:.1f}% de cobertura, "
                f"{reduction_portfolio['readiness_score']}% de preparación y aprobación formal registrada."
            ) if reduction_ready and approved else (
                f"El portafolio tiene {reduction_portfolio['action_count']} acción(es), "
                f"{reduction_portfolio['coverage_percent']:.1f}% de cobertura y "
                f"{reduction_portfolio['readiness_score']}% de preparación. Falta cerrar estructuración o aprobación."
                if reduction_started else "La entrega final requiere un portafolio de reducción y aprobación formal del inventario."
            ),
            "Completar portafolio" if not reduction_ready else "Completar aprobación",
            "/reduccion" if not reduction_ready else "/control",
            owner="Dirección y responsable climático",
            acceptance="Portafolio con cobertura suficiente, preparación mínima de 85%, sin acciones vencidas y aprobación formal.",
        ),
    ]

    weighted_total = sum(int(item["weight"]) for item in gates)
    score = round(sum(int(item["score"]) * int(item["weight"]) for item in gates) / max(weighted_total, 1))
    blockers = [item for item in gates if item["status"] == BLOCKED and bool(item["critical"])]
    warnings = [item for item in gates if item["status"] != READY and item not in blockers]
    next_gate = next((item for item in gates if item["status"] == BLOCKED), None) or next(
        (item for item in gates if item["status"] == PROGRESS), None
    )
    critical_pending = [item for item in gates if item["critical"] and item["status"] != READY]
    release_ready = not critical_pending and score >= 85 and approved
    publication = _publication_control(
        inventory,
        total=float(analysis["total"] or 0),
        score=score,
        release_ready=release_ready,
        critical_pending=critical_pending,
    )
    action_plan = _action_plan(gates)
    decision = _decision_brief(analysis, closure, publication)

    deliverables = [
        {
            "code": "ficha",
            "title": "Ficha ejecutiva para decisión",
            "format": "PDF",
            "status": READY if analysis["total"] > 0 else BLOCKED,
            "condition": publication["level"],
            "description": "Síntesis de resultado, confianza, focos, decisiones, prioridades y regla de publicación.",
        },
        {
            "code": "ejecutivo",
            "title": "Informe ejecutivo",
            "format": "PDF",
            "status": READY if analysis["total"] > 0 and quality_score >= 60 else BLOCKED,
            "condition": "Aprobado para emisión final" if approved else "Se emitirá como borrador hasta la aprobación",
            "description": "Resultados, concentración de emisiones, evolución, calidad, limitaciones y plan de reducción.",
        },
        {
            "code": "tecnico",
            "title": "Informe técnico",
            "format": "PDF",
            "status": READY if factor_ready and methodology_score >= 60 else PROGRESS,
            "condition": "Trazabilidad metodológica suficiente" if factor_ready else "Requiere cerrar factores o errores",
            "description": "Límites, metodología, factores, incertidumbre, fuentes, cálculos y declaración técnica.",
        },
        {
            "code": "editable",
            "title": "Informe de consultoría editable",
            "format": "Word",
            "status": READY if analysis["total"] > 0 and quality_score >= 50 else PROGRESS,
            "condition": "Borrador editable sujeto a revisión humana",
            "description": "Narrativa completa con comparación, intensidades, hallazgos, limitaciones, recomendaciones y anexos metodológicos.",
        },
        {
            "code": "memoria",
            "title": "Memoria de cálculo",
            "format": "Excel",
            "status": READY if calculation_count > 0 else BLOCKED,
            "condition": f"{calculation_count} cálculo(s) trazables disponibles",
            "description": "Datos de actividad, conversiones, factores, gases, fórmulas, resultados e indicadores.",
        },
    ]

    status_counts = {
        READY: sum(1 for item in gates if item["status"] == READY),
        PROGRESS: sum(1 for item in gates if item["status"] == PROGRESS),
        BLOCKED: sum(1 for item in gates if item["status"] == BLOCKED),
    }
    return {
        "score": score,
        "status": "Lista para entrega" if release_ready else ("En cierre" if score >= 60 else "En preparación"),
        "release_ready": release_ready,
        "approved": approved,
        "publication": publication,
        "decision": decision,
        "action_plan": action_plan,
        "gates": gates,
        "blockers": blockers,
        "warnings": warnings,
        "critical_pending": critical_pending,
        "next_action": next_gate,
        "deliverables": deliverables,
        "metrics": {
            "included_sources": len(included),
            "covered_sources": len(covered_sources),
            "coverage_ratio": coverage_ratio,
            "evidence_coverage": evidence_coverage,
            "quality_score": quality_score,
            "calculation_count": calculation_count,
            "open_observations": len(open_observations),
            "blocking_observations": len(blocking_observations),
            "methodology_score": methodology_score,
            "ready_gates": status_counts[READY],
            "progress_gates": status_counts[PROGRESS],
            "blocked_gates": status_counts[BLOCKED],
            "reduction_coverage": reduction_portfolio["coverage_percent"],
            "reduction_readiness": reduction_portfolio["readiness_score"],
            "reduction_gap": reduction_portfolio["gap"],
        },
        "narrative": _executive_narrative(inventory, analysis, closure, score),
        "analysis": analysis,
        "closure": closure,
    }
