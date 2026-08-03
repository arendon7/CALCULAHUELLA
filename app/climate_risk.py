from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import (
    ClimateRisk, ClimateRiskAssessment, ClimateRiskControl,
    ClimateTransitionAction, ClimateTransitionRoadmap, Inventory,
)

RISK_LEVELS = ((4, "Bajo"), (9, "Moderado"), (16, "Alto"), (25, "Crítico"))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def risk_level(score: float) -> str:
    for ceiling, label in RISK_LEVELS:
        if score <= ceiling:
            return label
    return "Crítico"


def calculate_risk_scores(likelihood: int, financial: int, operational: int, reputational: int, effectiveness: int) -> tuple[float, float]:
    likelihood = int(clamp(likelihood, 1, 5))
    impact = max(int(clamp(financial, 1, 5)), int(clamp(operational, 1, 5)), int(clamp(reputational, 1, 5)))
    inherent = float(likelihood * impact)
    residual = inherent * (1 - clamp(effectiveness, 0, 100) / 100)
    return round(inherent, 2), round(residual, 2)


def synchronize_control_effectiveness(session: Session, risk: ClimateRisk) -> None:
    controls = list(session.scalars(select(ClimateRiskControl).where(ClimateRiskControl.risk_id == risk.id)))
    implemented = [control.effectiveness for control in controls if control.status in {"Implementado", "Operando", "Verificado"}]
    if implemented:
        # La efectividad combinada evita sumar porcentajes como si fueran independientes.
        remaining = 1.0
        for effectiveness in implemented:
            remaining *= 1 - clamp(effectiveness, 0, 100) / 100
        risk.control_effectiveness = int(round((1 - remaining) * 100))
    inherent, residual = calculate_risk_scores(
        risk.likelihood, risk.financial_impact, risk.operational_impact,
        risk.reputational_impact, risk.control_effectiveness,
    )
    risk.inherent_score = inherent
    risk.residual_score = residual


def latest_assessment(session: Session, organization_id: int) -> ClimateRiskAssessment | None:
    return session.scalar(
        select(ClimateRiskAssessment)
        .where(ClimateRiskAssessment.organization_id == organization_id)
        .options(
            selectinload(ClimateRiskAssessment.risks).selectinload(ClimateRisk.controls),
            selectinload(ClimateRiskAssessment.roadmaps).selectinload(ClimateTransitionRoadmap.actions),
        )
        .order_by(ClimateRiskAssessment.updated_at.desc(), ClimateRiskAssessment.id.desc())
    )


def assessment_summary(session: Session, organization_id: int, assessment_id: int | None = None) -> dict[str, object]:
    assessment = session.get(ClimateRiskAssessment, assessment_id) if assessment_id else latest_assessment(session, organization_id)
    if not assessment or assessment.organization_id != organization_id:
        return {
            "assessment": None, "risks": [], "controls": [], "roadmap": None, "actions": [],
            "counts": {"total": 0, "physical": 0, "transition": 0, "opportunity": 0, "critical": 0},
            "financial": {"gross_exposure": 0.0, "residual_exposure": 0.0, "control_cost": 0.0, "avoided_exposure": 0.0, "opportunity_value": 0.0},
            "control_coverage": 0.0, "average_residual": 0.0, "readiness_score": 0,
            "matrix": [[0 for _ in range(5)] for _ in range(5)], "roadmap_metrics": {},
        }
    # Reload with relationships when called after session.get.
    risks = list(session.scalars(
        select(ClimateRisk).where(ClimateRisk.assessment_id == assessment.id)
        .options(selectinload(ClimateRisk.controls)).order_by(ClimateRisk.residual_score.desc(), ClimateRisk.id)
    ))
    controls = [control for risk in risks for control in risk.controls]
    roadmap = session.scalar(
        select(ClimateTransitionRoadmap).where(ClimateTransitionRoadmap.assessment_id == assessment.id)
        .options(selectinload(ClimateTransitionRoadmap.actions)).order_by(ClimateTransitionRoadmap.id.desc())
    )
    actions = list(roadmap.actions) if roadmap else []
    for risk in risks:
        synchronize_control_effectiveness(session, risk)
    downside_risks = [risk for risk in risks if risk.risk_type != "Oportunidad"]
    opportunities = [risk for risk in risks if risk.risk_type == "Oportunidad"]
    gross_exposure = sum(max(risk.financial_exposure, 0) for risk in downside_risks)
    residual_exposure = sum(max(risk.financial_exposure, 0) * (risk.residual_score / risk.inherent_score if risk.inherent_score else 0) for risk in downside_risks)
    opportunity_value = sum(max(risk.financial_exposure, 0) for risk in opportunities)
    control_cost = sum(max(control.annual_cost, 0) for control in controls)
    controlled_risks = sum(1 for risk in risks if risk.control_effectiveness > 0)
    control_coverage = controlled_risks / len(risks) * 100 if risks else 0
    average_residual = sum(risk.residual_score for risk in risks) / len(risks) if risks else 0
    matrix = [[0 for _ in range(5)] for _ in range(5)]
    for risk in risks:
        impact = max(risk.financial_impact, risk.operational_impact, risk.reputational_impact)
        matrix[5 - int(clamp(impact, 1, 5))][int(clamp(risk.likelihood, 1, 5)) - 1] += 1
    progress = sum(action.progress for action in actions) / len(actions) if actions else 0
    completed = sum(1 for action in actions if action.status == "Completada")
    action_coverage = min(100.0, len(actions) / max(len(risks), 1) * 100)
    governance = 100 if roadmap and roadmap.governance.strip() and roadmap.owner.strip() else 40 if roadmap else 0
    readiness = int(round(clamp(control_coverage * 0.30 + progress * 0.35 + action_coverage * 0.20 + governance * 0.15, 0, 100)))
    roadmap_metrics = {
        "progress": round(progress, 1), "completed": completed, "total": len(actions),
        "capex": round(sum(action.capex for action in actions), 2),
        "annual_opex": round(sum(action.annual_opex for action in actions), 2),
        "annual_savings": round(sum(action.annual_savings for action in actions), 2),
        "avoided_loss": round(sum(action.avoided_loss for action in actions), 2),
        "expected_reduction": round(sum(action.expected_reduction_tco2e for action in actions), 2),
    }
    return {
        "assessment": assessment, "risks": risks, "controls": controls, "roadmap": roadmap, "actions": actions,
        "counts": {
            "total": len(risks),
            "physical": sum(1 for risk in risks if risk.risk_type == "Físico"),
            "transition": sum(1 for risk in risks if risk.risk_type == "Transición"),
            "opportunity": sum(1 for risk in risks if risk.risk_type == "Oportunidad"),
            "critical": sum(1 for risk in risks if risk_level(risk.residual_score) == "Crítico"),
        },
        "financial": {
            "gross_exposure": round(gross_exposure, 2),
            "residual_exposure": round(residual_exposure, 2),
            "control_cost": round(control_cost, 2),
            "avoided_exposure": round(max(gross_exposure - residual_exposure, 0), 2),
            "opportunity_value": round(opportunity_value, 2),
        },
        "control_coverage": round(control_coverage, 1),
        "average_residual": round(average_residual, 2),
        "average_level": risk_level(average_residual),
        "readiness_score": readiness,
        "matrix": matrix,
        "roadmap_metrics": roadmap_metrics,
    }


def refresh_assessment_status(session: Session, assessment: ClimateRiskAssessment, user_email: str) -> None:
    summary = assessment_summary(session, assessment.organization_id, assessment.id)
    open_critical = summary["counts"]["critical"]
    if assessment.status == "Aprobada" and open_critical:
        assessment.status = "En tratamiento"
    assessment.reviewed_by = user_email
    assessment.reviewed_at = datetime.now(UTC)
