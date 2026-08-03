from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import (
    EmissionSource,
    Inventory,
    SupplierCampaign,
    SupplierDataRequest,
    SupplierResponse,
)

SUPPLIER_SOURCE_CATEGORY = "Datos específicos de proveedores"


def calculate_supplier_response(
    request: SupplierDataRequest,
    *,
    method: str,
    activity_value: float,
    emission_factor: float,
    reported_emissions_tco2e: float,
) -> float:
    """Return tCO2e using the response method.

    Factor-by-unit assumes the factor is expressed in kg CO2e per activity unit.
    Spend-based assumes kg CO2e per million COP.
    """
    if method == "Huella total suministrada":
        return max(0.0, reported_emissions_tco2e)
    if method == "Factor por gasto":
        return max(0.0, (request.spend_cop / 1_000_000) * emission_factor / 1000)
    return max(0.0, activity_value * emission_factor / 1000)


def quality_level(method: str, verified: bool, has_evidence: bool) -> str:
    if verified and has_evidence and method in {"Huella total suministrada", "Factor por unidad"}:
        return "A"
    if has_evidence and method in {"Huella total suministrada", "Factor por unidad"}:
        return "B"
    if method in {"Factor por unidad", "Factor por gasto"}:
        return "C"
    return "D"


def approved_supplier_emissions(session: Session, inventory_id: int) -> float:
    rows = session.scalars(
        select(SupplierResponse.calculated_emissions_tco2e)
        .join(SupplierDataRequest)
        .join(SupplierCampaign)
        .where(
            SupplierCampaign.inventory_id == inventory_id,
            SupplierResponse.review_status == "Aprobado",
        )
    ).all()
    return round(sum(rows), 6)


def sync_supplier_source(session: Session, inventory_id: int) -> EmissionSource:
    source = session.scalar(
        select(EmissionSource).where(
            EmissionSource.inventory_id == inventory_id,
            EmissionSource.category == SUPPLIER_SOURCE_CATEGORY,
        )
    )
    if not source:
        source = EmissionSource(
            inventory_id=inventory_id,
            facility_id=None,
            name="Bienes y servicios adquiridos",
            scope=3,
            category=SUPPLIER_SOURCE_CATEGORY,
            responsible="Compras sostenibles",
            materiality="Alta",
            data_frequency="Anual",
            preferred_unit="tCO₂e",
            included=True,
            icon="suppliers",
        )
        session.add(source)
        session.flush()
    total = approved_supplier_emissions(session, inventory_id)
    source.emissions = total
    requests = session.scalar(
        select(func.count()).select_from(SupplierDataRequest).join(SupplierCampaign).where(SupplierCampaign.inventory_id == inventory_id)
    ) or 0
    approved = session.scalar(
        select(func.count()).select_from(SupplierResponse).join(SupplierDataRequest).join(SupplierCampaign).where(
            SupplierCampaign.inventory_id == inventory_id,
            SupplierResponse.review_status == "Aprobado",
        )
    ) or 0
    source.progress = round(approved / requests * 100) if requests else 0
    source.status = "Completado" if requests and approved == requests else ("En progreso" if approved else "Pendiente")
    session.flush()
    return source


def campaign_summary(session: Session, campaign: SupplierCampaign) -> dict[str, object]:
    requests = list(
        session.scalars(
            select(SupplierDataRequest)
            .where(SupplierDataRequest.campaign_id == campaign.id)
            .options(
                selectinload(SupplierDataRequest.supplier),
                selectinload(SupplierDataRequest.response),
            )
            .order_by(SupplierDataRequest.due_date, SupplierDataRequest.id)
        )
    )
    responses = [item.response for item in requests if item.response]
    approved = [item for item in responses if item.review_status == "Aprobado"]
    total_spend = sum(item.spend_cop for item in requests)
    approved_spend = sum(item.spend_cop for item in requests if item.response and item.response.review_status == "Aprobado")
    quality_counts = Counter(item.quality_level for item in responses)
    return {
        "campaign": campaign,
        "requests": requests,
        "request_count": len(requests),
        "response_count": len(responses),
        "approved_count": len(approved),
        "response_rate": round(len(responses) / len(requests) * 100) if requests else 0,
        "approval_rate": round(len(approved) / len(requests) * 100) if requests else 0,
        "emissions": round(sum(item.calculated_emissions_tco2e for item in approved), 3),
        "total_spend": total_spend,
        "spend_coverage": round(approved_spend / total_spend * 100) if total_spend else 0,
        "quality_counts": {level: quality_counts.get(level, 0) for level in ("A", "B", "C", "D")},
    }


def inventory_supply_chain_summary(session: Session, inventory: Inventory) -> dict[str, object]:
    campaigns = list(
        session.scalars(
            select(SupplierCampaign)
            .where(SupplierCampaign.inventory_id == inventory.id)
            .options(selectinload(SupplierCampaign.requests).selectinload(SupplierDataRequest.response))
            .order_by(SupplierCampaign.created_at.desc())
        )
    )
    summaries = [campaign_summary(session, campaign) for campaign in campaigns]
    return {
        "campaigns": summaries,
        "campaign_count": len(campaigns),
        "request_count": sum(item["request_count"] for item in summaries),
        "response_count": sum(item["response_count"] for item in summaries),
        "approved_count": sum(item["approved_count"] for item in summaries),
        "emissions": round(sum(item["emissions"] for item in summaries), 3),
        "spend": sum(item["total_spend"] for item in summaries),
        "response_rate": round(sum(item["response_count"] for item in summaries) / max(sum(item["request_count"] for item in summaries), 1) * 100),
        "spend_coverage": round(
            sum(item["total_spend"] * item["spend_coverage"] / 100 for item in summaries) / max(sum(item["total_spend"] for item in summaries), 1) * 100
        ),
        "generated_at": datetime.now(UTC),
    }
