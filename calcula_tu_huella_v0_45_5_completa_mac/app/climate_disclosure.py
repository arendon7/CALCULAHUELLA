from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .climate_risk import assessment_summary, risk_level
from .database import (
    ClimateBoardBriefing,
    ClimateBoardDecision,
    ClimateDisclosureRequirement,
    ClimateDisclosureStatement,
    ClimateScenarioDefinition,
    EmissionSource,
    Inventory,
)


STATUS_WEIGHTS = {"Completo": 1.0, "Parcial": 0.5, "Pendiente": 0.0, "No aplica": 1.0}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def latest_inventory(session: Session, organization_id: int) -> Inventory | None:
    return session.scalar(
        select(Inventory)
        .where(Inventory.organization_id == organization_id)
        .order_by(Inventory.start_date.desc(), Inventory.id.desc())
    )


def scenario_comparison(session: Session, organization_id: int) -> dict[str, object]:
    scenarios = list(session.scalars(
        select(ClimateScenarioDefinition)
        .where(ClimateScenarioDefinition.organization_id == organization_id)
        .order_by(ClimateScenarioDefinition.id)
    ))
    risk_summary = assessment_summary(session, organization_id)
    risks = risk_summary["risks"]
    inventory = latest_inventory(session, organization_id)
    total_emissions = 0.0
    if inventory:
        total_emissions = sum(float(source.emissions or 0) for source in inventory.sources if source.included)

    active_scenarios = [scenario for scenario in scenarios if scenario.status != "Archivado"]
    roadmap = risk_summary.get("roadmap_metrics", {})
    results: list[dict[str, object]] = []
    for scenario in active_scenarios:
        downside_exposure = 0.0
        opportunity_value = 0.0
        adjusted_risks: list[dict[str, object]] = []
        critical = 0
        for risk in risks:
            if risk.risk_type == "Físico":
                multiplier = scenario.physical_multiplier
            elif risk.risk_type == "Transición":
                multiplier = scenario.transition_multiplier
            else:
                multiplier = scenario.opportunity_multiplier
            adjusted_score = round(clamp(risk.residual_score * multiplier, 0, 25), 2)
            adjusted_exposure = round(max(risk.financial_exposure, 0) * multiplier, 2)
            if risk.risk_type == "Oportunidad":
                opportunity_value += adjusted_exposure
            else:
                downside_exposure += adjusted_exposure
            if risk_level(adjusted_score) == "Crítico":
                critical += 1
            adjusted_risks.append({
                "risk": risk,
                "score": adjusted_score,
                "level": risk_level(adjusted_score),
                "exposure": adjusted_exposure,
                "multiplier": multiplier,
            })
        carbon_cost = total_emissions * max(scenario.carbon_price_2030, 0)
        transition_investment = float(roadmap.get("capex", 0) or 0) + float(roadmap.get("annual_opex", 0) or 0)
        annual_value = float(roadmap.get("annual_savings", 0) or 0) + float(roadmap.get("avoided_loss", 0) or 0)
        net_financial_pressure = max(downside_exposure + carbon_cost + transition_investment - annual_value - opportunity_value, 0)
        weighted_pressure = net_financial_pressure * clamp(scenario.probability_weight, 0, 100) / 100
        resilience_score = int(round(clamp(
            100 - (scenario.physical_multiplier - 1) * 28 - (scenario.transition_multiplier - 1) * 24
            + (scenario.opportunity_multiplier - 1) * 16 + risk_summary.get("readiness_score", 0) * 0.20,
            0, 100,
        )))
        results.append({
            "scenario": scenario,
            "downside_exposure": round(downside_exposure, 2),
            "opportunity_value": round(opportunity_value, 2),
            "carbon_cost": round(carbon_cost, 2),
            "transition_investment": round(transition_investment, 2),
            "annual_value": round(annual_value, 2),
            "net_financial_pressure": round(net_financial_pressure, 2),
            "weighted_pressure": round(weighted_pressure, 2),
            "resilience_score": resilience_score,
            "critical_risks": critical,
            "adjusted_risks": adjusted_risks,
        })
    results.sort(key=lambda item: item["net_financial_pressure"], reverse=True)
    probability_total = sum(max(item["scenario"].probability_weight, 0) for item in results)
    weighted_total = sum(float(item["weighted_pressure"]) for item in results)
    return {
        "scenarios": scenarios,
        "results": results,
        "inventory": inventory,
        "total_emissions": round(total_emissions, 2),
        "probability_total": round(probability_total, 1),
        "weighted_total": round(weighted_total, 2),
        "worst": results[0] if results else None,
        "best": results[-1] if results else None,
        "risk_summary": risk_summary,
    }


def latest_disclosure(session: Session, organization_id: int) -> ClimateDisclosureStatement | None:
    return session.scalar(
        select(ClimateDisclosureStatement)
        .where(ClimateDisclosureStatement.organization_id == organization_id)
        .options(selectinload(ClimateDisclosureStatement.requirements))
        .order_by(ClimateDisclosureStatement.updated_at.desc(), ClimateDisclosureStatement.id.desc())
    )


def disclosure_summary(session: Session, organization_id: int) -> dict[str, object]:
    statement = latest_disclosure(session, organization_id)
    if not statement:
        return {"statement": None, "requirements": [], "score": 0, "counts": {}, "pillars": []}
    requirements = sorted(statement.requirements, key=lambda item: (item.pillar, item.code))
    applicable = [item for item in requirements if item.status != "No aplica"]
    score = round(sum(STATUS_WEIGHTS.get(item.status, 0) for item in applicable) / len(applicable) * 100) if applicable else 100
    counts = {status: sum(1 for item in requirements if item.status == status) for status in STATUS_WEIGHTS}
    pillars: list[dict[str, object]] = []
    for pillar in dict.fromkeys(item.pillar for item in requirements):
        items = [item for item in requirements if item.pillar == pillar]
        applicable_items = [item for item in items if item.status != "No aplica"]
        pillar_score = round(sum(STATUS_WEIGHTS.get(item.status, 0) for item in applicable_items) / len(applicable_items) * 100) if applicable_items else 100
        pillars.append({"name": pillar, "score": pillar_score, "items": items})
    return {
        "statement": statement,
        "requirements": requirements,
        "score": score,
        "counts": counts,
        "pillars": pillars,
    }


def latest_briefing(session: Session, organization_id: int) -> ClimateBoardBriefing | None:
    return session.scalar(
        select(ClimateBoardBriefing)
        .where(ClimateBoardBriefing.organization_id == organization_id)
        .options(selectinload(ClimateBoardBriefing.decisions))
        .order_by(ClimateBoardBriefing.updated_at.desc(), ClimateBoardBriefing.id.desc())
    )


def board_summary(session: Session, organization_id: int) -> dict[str, object]:
    briefing = latest_briefing(session, organization_id)
    decisions = sorted(briefing.decisions, key=lambda item: (item.status == "Completada", item.due_date or date.max)) if briefing else []
    today = date.today()
    pending = [item for item in decisions if item.status not in {"Completada", "Cancelada"}]
    overdue = [item for item in pending if item.due_date and item.due_date < today]
    scenarios = scenario_comparison(session, organization_id)
    disclosure = disclosure_summary(session, organization_id)
    return {
        "briefing": briefing,
        "decisions": decisions,
        "pending": len(pending),
        "overdue": len(overdue),
        "scenarios": scenarios,
        "disclosure": disclosure,
        "risk_summary": scenarios["risk_summary"],
    }


def board_pack_payload(summary: dict[str, object], organization_name: str) -> str:
    briefing = summary["briefing"]
    scenarios = summary["scenarios"]
    disclosure = summary["disclosure"]
    risk_summary = summary["risk_summary"]
    parts = [
        organization_name,
        briefing.title if briefing else "Informe climático para comité directivo",
        str(briefing.meeting_date if briefing else ""),
        briefing.executive_summary if briefing else "",
        briefing.decisions_required if briefing else "",
        str(disclosure["score"]),
        str(risk_summary["financial"]["residual_exposure"]),
        str(scenarios["weighted_total"]),
    ]
    for item in summary["decisions"]:
        parts.extend([item.topic, item.decision, item.status, str(item.due_date or "")])
    return "|".join(parts)


def build_board_pdf(summary: dict[str, object], organization_name: str) -> tuple[bytes, str]:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm, title="Informe climático para comité directivo",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BoardTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.HexColor("#12344D"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#216B4E"), spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=7.6, leading=9.2))
    briefing = summary["briefing"]
    scenarios = summary["scenarios"]
    disclosure = summary["disclosure"]
    risk_summary = summary["risk_summary"]
    story = [
        Paragraph(escape(briefing.title if briefing else "Informe climático para comité directivo"), styles["BoardTitle"]),
        Paragraph(escape(f"{organization_name} · {briefing.audience if briefing else 'Comité directivo'} · {briefing.meeting_date.strftime('%d/%m/%Y') if briefing and briefing.meeting_date else 'Sin fecha definida'}"), styles["BodySmall"]),
        Spacer(1, 5 * mm),
    ]
    kpis = [
        ["Exposición residual", "Presión ponderada", "Preparación climática", "Divulgación", "Decisiones pendientes"],
        [
            f"${risk_summary['financial']['residual_exposure']:,.0f}",
            f"${scenarios['weighted_total']:,.0f}",
            f"{risk_summary['readiness_score']} %",
            f"{disclosure['score']} %",
            str(summary["pending"]),
        ],
    ]
    table = Table(kpis, colWidths=[48 * mm] * 5)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3EF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#216B4E")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 13),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D8D1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Paragraph("Síntesis ejecutiva", styles["Section"]), Paragraph(escape(briefing.executive_summary if briefing and briefing.executive_summary else "No se ha registrado una síntesis ejecutiva."), styles["BodySmall"])])
    story.append(Paragraph("Comparación de escenarios", styles["Section"]))
    scenario_rows = [["Escenario", "Trayectoria", "Probabilidad", "Exposición", "Costo carbono", "Oportunidad", "Presión neta", "Resiliencia"]]
    for result in scenarios["results"]:
        scenario = result["scenario"]
        scenario_rows.append([
            Paragraph(escape(scenario.name), styles["Cell"]), scenario.temperature_pathway,
            f"{scenario.probability_weight:.0f} %", f"${result['downside_exposure']:,.0f}",
            f"${result['carbon_cost']:,.0f}", f"${result['opportunity_value']:,.0f}",
            f"${result['net_financial_pressure']:,.0f}", f"{result['resilience_score']} / 100",
        ])
    scenario_table = Table(scenario_rows, colWidths=[42*mm, 27*mm, 23*mm, 32*mm, 30*mm, 30*mm, 32*mm, 25*mm], repeatRows=1)
    scenario_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12344D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.4),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
    ]))
    story.extend([scenario_table, PageBreak(), Paragraph("Decisiones y compromisos", styles["Section"])])
    decision_rows = [["Tema", "Decisión / propuesta", "Responsable", "Vencimiento", "Estado"]]
    for decision in summary["decisions"]:
        decision_rows.append([
            Paragraph(escape(decision.topic), styles["Cell"]), Paragraph(escape(decision.decision or decision.rationale), styles["Cell"]),
            decision.owner, decision.due_date.strftime("%d/%m/%Y") if decision.due_date else "", decision.status,
        ])
    if len(decision_rows) == 1:
        decision_rows.append(["Sin decisiones registradas", "", "", "", ""])
    decisions_table = Table(decision_rows, colWidths=[52*mm, 100*mm, 38*mm, 28*mm, 28*mm], repeatRows=1)
    decisions_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#216B4E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8F6")]),
    ]))
    story.extend([decisions_table, Paragraph("Estado de divulgación", styles["Section"])])
    pillar_rows = [["Pilar", "Avance", "Requisitos"]]
    for pillar in disclosure["pillars"]:
        pillar_rows.append([pillar["name"], f"{pillar['score']} %", str(len(pillar["items"]))])
    disclosure_table = Table(pillar_rows, colWidths=[100*mm, 35*mm, 35*mm])
    disclosure_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3EF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DA")),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(disclosure_table)
    payload = board_pack_payload(summary, organization_name)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    story.extend([Spacer(1, 6*mm), Paragraph(escape(f"Huella documental SHA-256: {digest}"), styles["BodySmall"]), Paragraph("Documento de gestión interna. Los escenarios y valores demostrativos deben validarse antes de decisiones financieras, regulatorias o públicas.", styles["BodySmall"])])
    doc.build(story)
    return buffer.getvalue(), digest
