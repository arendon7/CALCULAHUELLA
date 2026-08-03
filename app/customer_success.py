from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import (
    AccountHealthSnapshot,
    AppUser,
    BillingInvoice,
    CustomerOnboardingItem,
    CustomerSuccessProfile,
    Inventory,
    Organization,
    RenewalOpportunity,
    ServiceContract,
    ServiceOrder,
    SuccessCommitment,
    SupportTicket,
    ValueMilestone,
)


def _ratio(numerator: float, denominator: float, empty_score: float = 0.0) -> float:
    if denominator <= 0:
        return empty_score
    return max(0.0, min(1.0, numerator / denominator))


def _score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def account_metrics(session: Session, organization_id: int) -> dict[str, object]:
    organization = session.get(Organization, organization_id)
    if not organization:
        raise ValueError("Organización no encontrada")

    onboarding_total = session.scalar(
        select(func.count()).select_from(CustomerOnboardingItem).where(CustomerOnboardingItem.organization_id == organization_id)
    ) or 0
    onboarding_done = session.scalar(
        select(func.count()).select_from(CustomerOnboardingItem).where(
            CustomerOnboardingItem.organization_id == organization_id,
            CustomerOnboardingItem.status == "Completado",
        )
    ) or 0

    users_total = session.scalar(
        select(func.count()).select_from(AppUser).where(AppUser.organization_id == organization_id, AppUser.active.is_(True))
    ) or 0
    users_engaged = session.scalar(
        select(func.count()).select_from(AppUser).where(
            AppUser.organization_id == organization_id,
            AppUser.active.is_(True),
            AppUser.last_login.is_not(None),
        )
    ) or 0

    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == organization_id)))
    inventory_progress = round(sum(item.progress for item in inventories) / len(inventories), 1) if inventories else 0.0
    inventories_closed = sum(1 for item in inventories if item.status == "Cerrado" or item.locked)

    orders = list(session.scalars(select(ServiceOrder).where(ServiceOrder.organization_id == organization_id)))
    orders_accepted = sum(1 for item in orders if item.status == "Aceptada")
    orders_delivered = sum(1 for item in orders if item.status in {"Entregada", "Aceptada"})

    milestones = list(session.scalars(select(ValueMilestone).where(ValueMilestone.organization_id == organization_id)))
    milestones_completed = sum(1 for item in milestones if item.status == "Completado")
    realized_value = round(sum(item.realized_value for item in milestones if item.status == "Completado"), 2)

    open_tickets = list(session.scalars(select(SupportTicket).where(
        SupportTicket.organization_id == organization_id,
        SupportTicket.status.not_in(["Cerrado", "Resuelto"]),
    )))
    urgent_tickets = sum(1 for item in open_tickets if item.priority in {"Alta", "Urgente", "Crítica"})

    invoices = list(session.scalars(select(BillingInvoice).where(BillingInvoice.organization_id == organization_id)))
    invoices_paid = sum(1 for item in invoices if item.status == "Pagada")
    overdue_invoices = sum(
        1 for item in invoices
        if item.status not in {"Pagada", "Anulada"} and item.due_date and item.due_date < date.today()
    )

    contracts = list(session.scalars(select(ServiceContract).where(ServiceContract.organization_id == organization_id)))
    active_contracts = [item for item in contracts if item.status == "Vigente"]
    next_contract = min(
        (item for item in active_contracts if item.end_date),
        key=lambda item: item.end_date,
        default=None,
    )

    commitments = list(session.scalars(select(SuccessCommitment).where(SuccessCommitment.organization_id == organization_id)))
    commitments_done = sum(1 for item in commitments if item.status == "Completado")
    overdue_commitments = sum(
        1 for item in commitments
        if item.status != "Completado" and item.due_date and item.due_date < date.today()
    )

    profile = session.scalar(select(CustomerSuccessProfile).where(CustomerSuccessProfile.organization_id == organization_id))
    review_recent = False
    if profile and profile.last_business_review:
        review_recent = (date.today() - profile.last_business_review).days <= 120

    onboarding_component = _ratio(onboarding_done, onboarding_total, 0.5) * 100
    user_component = _ratio(users_engaged, users_total, 0.5) * 100
    inventory_component = inventory_progress
    adoption_score = _score(onboarding_component * 0.35 + user_component * 0.25 + inventory_component * 0.40)

    order_status_points = {"Planeada": 40, "En ejecución": 70, "Bloqueada": 10, "Entregada": 90, "Aceptada": 100, "Cancelada": 0}
    order_component = (
        sum(order_status_points.get(item.status, 30) for item in orders) / len(orders)
        if orders else 50
    )
    accepted_component = _ratio(orders_accepted, len(orders), 0.5) * 100
    milestone_status_points = {"Planeado": 25, "En progreso": 60, "Completado": 100, "Cancelado": 0}
    milestone_component = (
        sum(milestone_status_points.get(item.status, 25) for item in milestones) / len(milestones)
        if milestones else 50
    )
    delivery_score = _score(order_component * 0.35 + accepted_component * 0.25 + milestone_component * 0.40)

    support_penalty = min(75, len(open_tickets) * 12 + urgent_tickets * 18)
    support_score = _score(100 - support_penalty)

    if invoices:
        payment_health = max(0, 100 - (overdue_invoices / len(invoices) * 100))
    else:
        payment_health = 70
    contract_component = 100 if active_contracts else 45 if contracts else 25
    commercial_score = _score(payment_health * 0.45 + contract_component * 0.55)

    commitment_component = _ratio(commitments_done, len(commitments), 0.5) * 100
    review_component = 100 if review_recent else 55 if profile and profile.next_business_review else 30
    satisfaction_component = (profile.satisfaction_score / 5 * 100) if profile and profile.satisfaction_score is not None else 60
    engagement_score = _score(commitment_component * 0.35 + review_component * 0.30 + satisfaction_component * 0.35 - min(30, overdue_commitments * 10))

    overall_score = _score(
        adoption_score * 0.30
        + delivery_score * 0.20
        + support_score * 0.15
        + commercial_score * 0.20
        + engagement_score * 0.15
    )

    if profile and profile.risk_override:
        risk_level = profile.risk_override
    elif overall_score >= 80:
        risk_level = "Sano"
    elif overall_score >= 65:
        risk_level = "Atención"
    elif overall_score >= 45:
        risk_level = "Riesgo"
    else:
        risk_level = "Crítico"

    recommendations: list[str] = []
    if adoption_score < 70:
        recommendations.append("Aumentar adopción: completar onboarding, activar usuarios y cerrar brechas del inventario.")
    if delivery_score < 70:
        recommendations.append("Asegurar entregables: convertir órdenes e hitos en resultados aceptados por el cliente.")
    if urgent_tickets:
        recommendations.append(f"Resolver {urgent_tickets} caso(s) prioritario(s) de soporte.")
    if overdue_invoices:
        recommendations.append(f"Regularizar {overdue_invoices} cobro(s) vencido(s) antes de negociar renovación.")
    if not review_recent:
        recommendations.append("Programar una revisión ejecutiva de valor con patrocinador y responsables.")
    if not recommendations:
        recommendations.append("Mantener cadencia ejecutiva y documentar valor realizado para preparar expansión o renovación.")

    days_to_renewal = None
    if next_contract and next_contract.end_date:
        days_to_renewal = (next_contract.end_date - date.today()).days

    return {
        "organization": organization,
        "profile": profile,
        "onboarding_total": onboarding_total,
        "onboarding_done": onboarding_done,
        "users_total": users_total,
        "users_engaged": users_engaged,
        "inventories_total": len(inventories),
        "inventories_closed": inventories_closed,
        "inventory_progress": inventory_progress,
        "orders_total": len(orders),
        "orders_accepted": orders_accepted,
        "milestones_total": len(milestones),
        "milestones_completed": milestones_completed,
        "realized_value": realized_value,
        "open_tickets": len(open_tickets),
        "urgent_tickets": urgent_tickets,
        "invoices_total": len(invoices),
        "invoices_paid": invoices_paid,
        "overdue_invoices": overdue_invoices,
        "active_contracts": len(active_contracts),
        "days_to_renewal": days_to_renewal,
        "commitments_total": len(commitments),
        "commitments_done": commitments_done,
        "overdue_commitments": overdue_commitments,
        "adoption_score": adoption_score,
        "delivery_score": delivery_score,
        "support_score": support_score,
        "commercial_score": commercial_score,
        "engagement_score": engagement_score,
        "overall_score": overall_score,
        "risk_level": risk_level,
        "recommendation": " ".join(recommendations),
        "next_contract": next_contract,
    }


def refresh_account_health(session: Session, organization_id: int, created_by: str = "sistema") -> AccountHealthSnapshot:
    metrics = account_metrics(session, organization_id)
    serializable = {
        key: value
        for key, value in metrics.items()
        if key not in {"organization", "profile", "next_contract"}
    }
    snapshot = AccountHealthSnapshot(
        organization_id=organization_id,
        overall_score=int(metrics["overall_score"]),
        adoption_score=int(metrics["adoption_score"]),
        delivery_score=int(metrics["delivery_score"]),
        support_score=int(metrics["support_score"]),
        commercial_score=int(metrics["commercial_score"]),
        engagement_score=int(metrics["engagement_score"]),
        risk_level=str(metrics["risk_level"]),
        recommendation=str(metrics["recommendation"]),
        metrics_json=json.dumps(serializable, ensure_ascii=False, default=str),
        calculated_at=datetime.now(UTC),
        created_by=created_by,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def sync_renewal_opportunity(
    session: Session,
    organization_id: int,
    snapshot: AccountHealthSnapshot,
    updated_by: str = "sistema",
) -> RenewalOpportunity | None:
    contract = session.scalar(
        select(ServiceContract)
        .where(ServiceContract.organization_id == organization_id, ServiceContract.status == "Vigente")
        .order_by(ServiceContract.end_date)
    )
    if not contract:
        return None

    opportunity = session.scalar(select(RenewalOpportunity).where(RenewalOpportunity.contract_id == contract.id))
    if not opportunity:
        opportunity = RenewalOpportunity(
            organization_id=organization_id,
            contract_id=contract.id,
            renewal_date=contract.end_date,
            forecast_amount=contract.contract_value,
            updated_by=updated_by,
        )
        session.add(opportunity)

    probability = snapshot.overall_score
    overdue = session.scalar(
        select(func.count()).select_from(BillingInvoice).where(
            BillingInvoice.organization_id == organization_id,
            BillingInvoice.status.not_in(["Pagada", "Anulada"]),
            BillingInvoice.due_date < date.today(),
        )
    ) or 0
    if overdue:
        probability -= min(35, overdue * 20)
    opportunity.probability = max(5, min(95, probability))
    opportunity.renewal_date = contract.end_date
    opportunity.forecast_amount = contract.contract_value
    opportunity.updated_by = updated_by
    if opportunity.probability >= 80:
        opportunity.status = "Bien encaminada"
        opportunity.next_action = opportunity.next_action or "Preparar conversación de renovación y expansión basada en valor realizado."
    elif opportunity.probability >= 60:
        opportunity.status = "Por preparar"
        opportunity.next_action = opportunity.next_action or "Cerrar brechas de adopción y presentar plan de valor antes de la renovación."
    else:
        opportunity.status = "En riesgo"
        opportunity.next_action = opportunity.next_action or "Activar plan de recuperación ejecutivo con responsables, fechas y bloqueadores."
    session.flush()
    return opportunity
