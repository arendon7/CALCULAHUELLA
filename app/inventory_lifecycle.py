from __future__ import annotations

import re
import secrets

from sqlalchemy.orm import Session

from .calculations import recalculate_inventory
from .database import refresh_progress
from .db.models import (
    ActivityData,
    ActivityIndicator,
    EmissionSource,
    EmissionTarget,
    EvidenceDocument,
    Inventory,
    InventoryFacility,
    ReductionAction,
    ReductionScenario,
    ReductionScenarioAction,
    ReviewObservation,
    SourceFactorAssignment,
    SupplierCampaign,
    SupplierDataRequest,
    SupplierResponse,
)


def next_inventory_version(version: str) -> str:
    version = version or "1.0"
    match = re.search(r"-r(\d+)$", version)
    if match:
        return re.sub(r"-r(\d+)$", lambda m: f"-r{int(m.group(1)) + 1}", version)
    return f"{version}-r1"

def clone_inventory_version(session: Session, inventory: Inventory, user: dict[str, object], reason: str) -> Inventory:
    new_inventory = Inventory(
        organization_id=inventory.organization_id,
        name=f"{inventory.name} · revisión",
        start_date=inventory.start_date,
        end_date=inventory.end_date,
        objective=inventory.objective,
        base_year=inventory.base_year,
        methodology=inventory.methodology,
        methodology_version=inventory.methodology_version,
        gwp_version=inventory.gwp_version,
        consolidation_approach=inventory.consolidation_approach,
        materiality_threshold=inventory.materiality_threshold,
        status="Borrador",
        progress=inventory.progress,
        current_stage="Corrección",
        notes=f"Nueva versión creada desde el inventario cerrado #{inventory.id}. Motivo: {reason}",
        version=next_inventory_version(inventory.version),
        parent_inventory_id=inventory.id,
        locked=False,
    )
    session.add(new_inventory)
    session.flush()
    for link in inventory.facility_links:
        session.add(InventoryFacility(
            inventory_id=new_inventory.id,
            facility_id=link.facility_id,
            included=link.included,
            inclusion_percentage=link.inclusion_percentage,
            exclusion_reason=link.exclusion_reason,
        ))
    source_map: dict[int, EmissionSource] = {}
    for old_source in inventory.sources:
        new_source = EmissionSource(
            inventory_id=new_inventory.id,
            facility_id=old_source.facility_id,
            name=old_source.name,
            scope=old_source.scope,
            category=old_source.category,
            responsible=old_source.responsible,
            materiality=old_source.materiality,
            data_frequency=old_source.data_frequency,
            preferred_unit=old_source.preferred_unit,
            included=old_source.included,
            exclusion_reason=old_source.exclusion_reason,
            progress=old_source.progress,
            status=old_source.status,
            emissions=old_source.emissions,
            unit=old_source.unit,
            icon=old_source.icon,
        )
        session.add(new_source)
        session.flush()
        source_map[old_source.id] = new_source
        for assignment in old_source.factor_assignments:
            session.add(SourceFactorAssignment(
                source_id=new_source.id,
                factor_version_id=assignment.factor_version_id,
                active=assignment.active,
                assigned_by=str(user["email"]),
                notes=f"Copiado desde inventario #{inventory.id}",
            ))
    document_map: dict[int, EvidenceDocument] = {}
    for old_document in inventory.documents:
        new_document = EvidenceDocument(
            inventory_id=new_inventory.id,
            source_id=source_map[old_document.source_id].id if old_document.source_id in source_map else None,
            name=old_document.name,
            stored_name=old_document.stored_name,
            document_type=old_document.document_type,
            source_name=old_document.source_name,
            period_label=old_document.period_label,
            status=old_document.status,
            uploaded_by=old_document.uploaded_by,
            uploaded_at=old_document.uploaded_at,
            file_size=old_document.file_size,
            sha256=old_document.sha256,
            notes=f"Referencia heredada del inventario #{inventory.id}. {old_document.notes}",
        )
        session.add(new_document)
        session.flush()
        document_map[old_document.id] = new_document
    for old_source in inventory.sources:
        new_source = source_map[old_source.id]
        for old_record in old_source.activity_records:
            session.add(ActivityData(
                source_id=new_source.id,
                evidence_id=document_map[old_record.evidence_id].id if old_record.evidence_id in document_map else None,
                period_start=old_record.period_start,
                period_end=old_record.period_end,
                value=old_record.value,
                unit=old_record.unit,
                data_origin=old_record.data_origin,
                quality_level=old_record.quality_level,
                is_estimated=old_record.is_estimated,
                notes=old_record.notes,
                status="En revisión" if old_record.status == "Aprobado" else old_record.status,
                created_by=str(user["email"]),
            ))
    for old_indicator in inventory.indicators:
        session.add(ActivityIndicator(
            inventory_id=new_inventory.id, facility_id=old_indicator.facility_id, evidence_id=None,
            period_start=old_indicator.period_start, period_end=old_indicator.period_end,
            indicator_type=old_indicator.indicator_type, value=old_indicator.value, unit=old_indicator.unit,
            source_name=old_indicator.source_name, notes=old_indicator.notes, status="En revisión",
            created_by=str(user["email"]),
        ))
    action_map: dict[int, ReductionAction] = {}
    for old_action in inventory.reduction_actions:
        new_action = ReductionAction(
            inventory_id=new_inventory.id,
            source_id=source_map[old_action.source_id].id if old_action.source_id in source_map else None,
            title=old_action.title, description=old_action.description, baseline_emissions=old_action.baseline_emissions,
            expected_reduction=old_action.expected_reduction, investment_cost=old_action.investment_cost,
            annual_savings=old_action.annual_savings, priority=old_action.priority, responsible=old_action.responsible,
            target_date=old_action.target_date, status=old_action.status, progress_percent=old_action.progress_percent,
            actual_reduction=old_action.actual_reduction, actual_savings=old_action.actual_savings,
            useful_life_years=old_action.useful_life_years, implementation_year=old_action.implementation_year,
            feasibility=old_action.feasibility, risk_level=old_action.risk_level,
            created_by=str(user["email"]),
        )
        session.add(new_action)
        session.flush()
        action_map[old_action.id] = new_action
    for old_target in inventory.targets:
        session.add(EmissionTarget(
            inventory_id=new_inventory.id, name=old_target.name, metric_type=old_target.metric_type,
            baseline_year=old_target.baseline_year, target_year=old_target.target_year,
            baseline_value=old_target.baseline_value, target_value=old_target.target_value,
            current_value=old_target.current_value, unit=old_target.unit, status=old_target.status,
            notes=old_target.notes, created_by=str(user["email"]),
        ))
    for old_scenario in inventory.reduction_scenarios:
        new_scenario = ReductionScenario(
            inventory_id=new_inventory.id, name=old_scenario.name, description=old_scenario.description,
            start_year=old_scenario.start_year, target_year=old_scenario.target_year,
            discount_rate=old_scenario.discount_rate, status="Borrador", created_by=str(user["email"]),
        )
        session.add(new_scenario)
        session.flush()
        for old_link in old_scenario.action_links:
            if old_link.action_id in action_map:
                session.add(ReductionScenarioAction(
                    scenario_id=new_scenario.id, action_id=action_map[old_link.action_id].id,
                    included=old_link.included, implementation_year=old_link.implementation_year,
                    adoption_percent=old_link.adoption_percent,
                ))
    for old_campaign in inventory.supplier_campaigns:
        new_campaign = SupplierCampaign(
            inventory_id=new_inventory.id, name=old_campaign.name, category=old_campaign.category,
            due_date=old_campaign.due_date, status="Borrador", methodology=old_campaign.methodology,
            description=f"Copiada del inventario #{inventory.id}. {old_campaign.description}", created_by=str(user["email"]),
        )
        session.add(new_campaign)
        session.flush()
        for old_request in old_campaign.requests:
            new_request = SupplierDataRequest(
                campaign_id=new_campaign.id, supplier_id=old_request.supplier_id, product_service=old_request.product_service,
                quantity=old_request.quantity, unit=old_request.unit, spend_cop=old_request.spend_cop,
                requested_method=old_request.requested_method, status="Pendiente", due_date=old_request.due_date,
                access_token=secrets.token_urlsafe(24), token_expires_at=old_request.token_expires_at, notes=old_request.notes,
            )
            session.add(new_request)
            session.flush()
            if old_request.response:
                old_response = old_request.response
                session.add(SupplierResponse(
                    request_id=new_request.id, method=old_response.method, activity_value=old_response.activity_value,
                    activity_unit=old_response.activity_unit, emission_factor=old_response.emission_factor, factor_unit=old_response.factor_unit,
                    reported_emissions_tco2e=old_response.reported_emissions_tco2e, calculated_emissions_tco2e=old_response.calculated_emissions_tco2e,
                    methodology=old_response.methodology, boundary=old_response.boundary, verified=old_response.verified,
                    quality_level=old_response.quality_level, evidence_name=old_response.evidence_name,
                    evidence_stored_name=old_response.evidence_stored_name, evidence_sha256=old_response.evidence_sha256,
                    evidence_size=old_response.evidence_size, notes=old_response.notes, review_status="Pendiente",
                ))
    session.add(ReviewObservation(
        inventory_id=new_inventory.id,
        entity_type="Inventario",
        entity_label=new_inventory.name,
        title="Revisión generada por reapertura",
        description=reason,
        severity="Mayor",
        status="Abierta",
        assigned_to=str(user["name"]),
        created_by=str(user["email"]),
    ))
    session.flush()
    refresh_progress(session, new_inventory)
    recalculate_inventory(session, new_inventory)
    return new_inventory
