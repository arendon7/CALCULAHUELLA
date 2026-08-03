from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import Inventory, ReductionAction, ReductionScenario, ReductionScenarioAction


@dataclass
class ActionEconomics:
    action_id: int
    title: str
    reduction: float
    investment: float
    annual_savings: float
    annualized_capex: float
    net_annual_cost: float
    marginal_cost: float
    payback_years: float | None
    implementation_year: int | None
    feasibility: str
    risk_level: str


def capital_recovery_factor(discount_rate_percent: float, years: int) -> float:
    years = max(int(years or 1), 1)
    rate = max(discount_rate_percent, 0.0) / 100.0
    if rate == 0:
        return 1.0 / years
    factor = (1 + rate) ** years
    return rate * factor / (factor - 1)


def action_economics(action: ReductionAction, discount_rate: float = 10.0, adoption_percent: float = 100.0, implementation_year: int | None = None) -> ActionEconomics:
    adoption = max(0.0, min(100.0, adoption_percent)) / 100.0
    reduction = max(action.expected_reduction, 0.0) * adoption
    investment = max(action.investment_cost, 0.0) * adoption
    savings = max(action.annual_savings, 0.0) * adoption
    crf = capital_recovery_factor(discount_rate, action.useful_life_years)
    annualized_capex = investment * crf
    net_annual_cost = annualized_capex - savings
    marginal_cost = net_annual_cost / reduction if reduction > 0 else 0.0
    payback = investment / savings if savings > 0 else None
    return ActionEconomics(
        action_id=action.id,
        title=action.title,
        reduction=round(reduction, 6),
        investment=round(investment, 2),
        annual_savings=round(savings, 2),
        annualized_capex=round(annualized_capex, 2),
        net_annual_cost=round(net_annual_cost, 2),
        marginal_cost=round(marginal_cost, 2),
        payback_years=round(payback, 2) if payback is not None else None,
        implementation_year=implementation_year or action.implementation_year,
        feasibility=action.feasibility,
        risk_level=action.risk_level,
    )


def get_scenario(session: Session, scenario_id: int, organization_id: int) -> ReductionScenario | None:
    return session.scalar(
        select(ReductionScenario)
        .join(Inventory)
        .where(ReductionScenario.id == scenario_id, Inventory.organization_id == organization_id)
        .options(
            selectinload(ReductionScenario.inventory).selectinload(Inventory.reduction_actions),
            selectinload(ReductionScenario.action_links).selectinload(ReductionScenarioAction.action),
        )
    )


def scenario_summary(scenario: ReductionScenario) -> dict[str, object]:
    baseline = sum(source.emissions for source in scenario.inventory.sources if source.included)
    economics: list[ActionEconomics] = []
    for link in scenario.action_links:
        if not link.included:
            continue
        economics.append(action_economics(
            link.action,
            scenario.discount_rate,
            link.adoption_percent,
            link.implementation_year,
        ))
    total_reduction = sum(item.reduction for item in economics)
    investment = sum(item.investment for item in economics)
    savings = sum(item.annual_savings for item in economics)
    net_cost = sum(item.net_annual_cost for item in economics)
    projected = max(0.0, baseline - total_reduction)
    average_cost = net_cost / total_reduction if total_reduction else 0.0
    timeline = []
    cumulative = 0.0
    for year in range(scenario.start_year, scenario.target_year + 1):
        annual = sum(item.reduction for item in economics if (item.implementation_year or scenario.start_year) <= year)
        cumulative = annual
        timeline.append({"year": year, "emissions": max(0.0, baseline - cumulative), "reduction": cumulative})
    macc = sorted(economics, key=lambda item: item.marginal_cost)
    max_abs_cost = max([abs(item.marginal_cost) for item in macc] + [1.0])
    return {
        "baseline": round(baseline, 3),
        "projected_emissions": round(projected, 3),
        "total_reduction": round(total_reduction, 3),
        "reduction_percent": round(total_reduction / baseline * 100, 2) if baseline else 0.0,
        "investment": round(investment, 2),
        "annual_savings": round(savings, 2),
        "net_annual_cost": round(net_cost, 2),
        "average_marginal_cost": round(average_cost, 2),
        "actions": economics,
        "macc": macc,
        "macc_max_abs_cost": max_abs_cost,
        "timeline": timeline,
    }


def portfolio_macc(actions: list[ReductionAction], discount_rate: float = 10.0) -> list[ActionEconomics]:
    rows = [action_economics(action, discount_rate) for action in actions if action.expected_reduction > 0]
    return sorted(rows, key=lambda item: item.marginal_cost)
