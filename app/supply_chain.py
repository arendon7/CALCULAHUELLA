from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import (
    EmissionSource,
    Inventory,
    SupplierCampaign,
    Scope3CategoryAssessment,
    SupplierDataRequest,
    SupplierResponse,
    refresh_inventory_progress,
)
from .scope3_catalog import SCOPE3_CATEGORIES, canonical_category_label, category_catalog, category_from_value

SUPPLIER_SOURCE_CATEGORY = "Datos específicos de proveedores"
SUPPORTED_SUPPLIER_METHODS = {"Huella total suministrada", "Factor por unidad", "Factor por gasto"}
SCOPE3_ASSESSMENT_STATUSES = {"Pendiente", "Material", "No material", "No aplica"}


def ensure_scope3_assessments(session: Session, inventory_id: int) -> list[Scope3CategoryAssessment]:
    existing = list(session.scalars(
        select(Scope3CategoryAssessment).where(Scope3CategoryAssessment.inventory_id == inventory_id)
    ))
    by_code = {item.category_code: item for item in existing}
    campaign_categories = {
        category.code
        for value in session.scalars(select(SupplierCampaign.category).where(SupplierCampaign.inventory_id == inventory_id))
        if (category := category_from_value(value)) is not None
    }
    for category in SCOPE3_CATEGORIES:
        assessment = by_code.get(category.code)
        if assessment is None:
            assessment = Scope3CategoryAssessment(
                inventory_id=inventory_id,
                category_code=category.code,
                status="Material" if category.code in campaign_categories else "Pendiente",
                relevance_score=4 if category.code in campaign_categories else 0,
                rationale="Categoría priorizada por una campaña existente." if category.code in campaign_categories else "",
                data_strategy="Campaña de proveedores" if category.code in campaign_categories else "Por definir",
            )
            session.add(assessment)
            by_code[category.code] = assessment
        elif assessment.status == "Pendiente" and category.code in campaign_categories:
            assessment.status = "Material"
            assessment.relevance_score = max(assessment.relevance_score, 4)
            assessment.rationale = assessment.rationale or "Categoría priorizada por una campaña existente."
            assessment.data_strategy = assessment.data_strategy if assessment.data_strategy != "Por definir" else "Campaña de proveedores"
    session.flush()
    return [by_code[category.code] for category in SCOPE3_CATEGORIES]


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_unit(value: str) -> str:
    normalized = _normalize(value).replace("toneladas", "t").replace("tonelada", "t")
    normalized = normalized.replace("kilogramos", "kg").replace("kilogramo", "kg")
    normalized = normalized.replace("unidades", "unidad")
    normalized = normalized.replace("millones cop", "millon cop").replace("millón cop", "millon cop")
    return normalized


def _factor_denominator(factor_unit: str) -> str:
    if "/" in (factor_unit or ""):
        return _normalize_unit(factor_unit.rsplit("/", 1)[-1])
    match = re.search(r"\bpor\s+(.+)$", factor_unit or "", flags=re.IGNORECASE)
    return _normalize_unit(match.group(1)) if match else ""


def calculate_supplier_response(
    request: SupplierDataRequest,
    *,
    method: str,
    activity_value: float,
    emission_factor: float,
    reported_emissions_tco2e: float,
) -> float:
    """Return tCO2e using the selected response method.

    Factor-by-unit assumes kg CO2e per declared activity unit.
    Spend-based assumes kg CO2e per million COP.
    Input compatibility is checked by ``validate_supplier_response`` before approval.
    """
    if method == "Huella total suministrada":
        return max(0.0, reported_emissions_tco2e)
    if method == "Factor por gasto":
        return max(0.0, (request.spend_cop / 1_000_000) * emission_factor / 1000)
    return max(0.0, activity_value * emission_factor / 1000)


def validate_supplier_response(
    request: SupplierDataRequest,
    *,
    method: str,
    activity_value: float,
    activity_unit: str,
    emission_factor: float,
    factor_unit: str,
    reported_emissions_tco2e: float,
    methodology: str = "",
    boundary: str = "",
    has_evidence: bool = False,
) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if method not in SUPPORTED_SUPPLIER_METHODS:
        errors.append("El método de respuesta no está soportado.")
        return {"errors": errors, "warnings": warnings}

    if method == "Huella total suministrada":
        if reported_emissions_tco2e <= 0:
            errors.append("La huella total suministrada debe ser mayor que cero.")
    elif method == "Factor por gasto":
        if request.spend_cop <= 0:
            errors.append("El método por gasto requiere un valor de compra mayor que cero.")
        if emission_factor <= 0:
            errors.append("El factor por gasto debe ser mayor que cero.")
        normalized_factor = _normalize(factor_unit)
        if "kg" not in normalized_factor or "cop" not in normalized_factor:
            errors.append("El factor por gasto debe declararse en kg CO₂e por millón COP.")
        warnings.append("El método por gasto es una aproximación secundaria; debe sustituirse por datos físicos o específicos cuando sea material.")
    else:
        if activity_value <= 0:
            errors.append("El dato de actividad debe ser mayor que cero.")
        if emission_factor <= 0:
            errors.append("El factor de emisión debe ser mayor que cero.")
        if not activity_unit.strip():
            errors.append("La unidad del dato de actividad es obligatoria.")
        normalized_factor = _normalize(factor_unit)
        if "kg" not in normalized_factor or "co2" not in normalized_factor:
            errors.append("El factor por unidad debe expresarse en kg CO₂e por unidad de actividad.")
        denominator = _factor_denominator(factor_unit)
        activity_normalized = _normalize_unit(activity_unit)
        if not denominator:
            errors.append("La unidad del factor debe indicar su denominador, por ejemplo kg CO₂e/t.")
        elif activity_normalized and denominator != activity_normalized:
            errors.append(
                f"La unidad del factor ({denominator}) no coincide con la unidad de actividad ({activity_normalized})."
            )
        if request.quantity > 0 and activity_value > 0:
            difference = abs(activity_value - request.quantity) / max(request.quantity, 1e-12)
            if difference > 0.10:
                warnings.append("El dato reportado difiere en más de 10 % de la cantidad solicitada; documenta la conciliación.")

    if not methodology.strip():
        warnings.append("No se indicó la metodología o fuente del dato.")
    if not boundary.strip():
        warnings.append("No se documentaron los límites del cálculo.")
    if not has_evidence:
        warnings.append("La respuesta no contiene evidencia técnica adjunta.")

    category = category_from_value(request.campaign.category if request.campaign else None)
    boundary_normalized = _normalize(boundary)
    if category and category.number in {1, 2} and boundary.strip() and not any(
        token in boundary_normalized for token in ("cradle to gate", "cuna a puerta", "puerta del proveedor")
    ):
        warnings.append("Para esta categoría debe aclararse si el límite es cradle-to-gate o equivalente.")
    return {"errors": errors, "warnings": warnings}


def quality_level(method: str, verified: bool, has_evidence: bool) -> str:
    # Preserve the persisted A-D convention while exposing a richer dynamic passport separately.
    if verified and has_evidence and method in {"Huella total suministrada", "Factor por unidad"}:
        return "A"
    if has_evidence and method in {"Huella total suministrada", "Factor por unidad"}:
        return "B"
    if method in {"Factor por unidad", "Factor por gasto"}:
        return "C"
    return "D"


def response_quality_passport(response: SupplierResponse | None) -> dict[str, object]:
    if not response:
        return {"score": 0, "level": "D", "dimensions": {}, "warnings": ["Sin respuesta del proveedor."]}
    method_score = {
        "Huella total suministrada": 30,
        "Factor por unidad": 28,
        "Factor por gasto": 12,
    }.get(response.method, 0)
    dimensions = {
        "método": method_score,
        "evidencia": 20 if response.evidence_stored_name else 0,
        "verificación": 15 if response.verified else 0,
        "metodología": 12 if response.methodology.strip() else 0,
        "límites": 12 if response.boundary.strip() else 0,
        "revisión": 6 if response.review_status == "Aprobado" else 0,
        "unidad": 5 if response.method != "Factor por unidad" or _factor_denominator(response.factor_unit) else 0,
    }
    score = min(100, sum(dimensions.values()))
    level = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 45 else "D"
    warnings: list[str] = []
    if response.method == "Factor por gasto":
        warnings.append("Dato secundario basado en gasto.")
    if not response.evidence_stored_name:
        warnings.append("Sin evidencia adjunta.")
    if not response.verified:
        warnings.append("Sin verificación independiente declarada.")
    return {"score": score, "level": level, "dimensions": dimensions, "warnings": warnings}


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
            name="Cadena de valor consolidada desde proveedores",
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
    else:
        source.name = "Cadena de valor consolidada desde proveedores"
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
    inventory = session.get(Inventory, inventory_id)
    if inventory is not None:
        refresh_inventory_progress(session, inventory)
    return source


def response_duplicate_key(response: SupplierResponse) -> tuple[str, int, str]:
    request = response.request
    category = category_from_value(request.campaign.category)
    return (
        category.code if category else _normalize(request.campaign.category),
        request.supplier_id,
        _normalize(request.product_service),
    )


def approved_duplicate_responses(
    session: Session,
    response: SupplierResponse,
) -> list[SupplierResponse]:
    inventory_id = response.request.campaign.inventory_id
    candidates = list(
        session.scalars(
            select(SupplierResponse)
            .join(SupplierDataRequest)
            .join(SupplierCampaign)
            .where(
                SupplierCampaign.inventory_id == inventory_id,
                SupplierResponse.review_status == "Aprobado",
                SupplierResponse.id != response.id,
            )
            .options(
                selectinload(SupplierResponse.request).selectinload(SupplierDataRequest.campaign),
                selectinload(SupplierResponse.request).selectinload(SupplierDataRequest.supplier),
            )
        )
    )
    key = response_duplicate_key(response)
    return [candidate for candidate in candidates if response_duplicate_key(candidate) == key]


def campaign_summary(session: Session, campaign: SupplierCampaign) -> dict[str, object]:
    requests = list(
        session.scalars(
            select(SupplierDataRequest)
            .where(SupplierDataRequest.campaign_id == campaign.id)
            .options(
                selectinload(SupplierDataRequest.supplier),
                selectinload(SupplierDataRequest.response),
                selectinload(SupplierDataRequest.campaign),
            )
            .order_by(SupplierDataRequest.due_date, SupplierDataRequest.id)
        )
    )
    responses = [item.response for item in requests if item.response]
    approved = [item for item in responses if item.review_status == "Aprobado"]
    total_spend = sum(item.spend_cop for item in requests)
    approved_spend = sum(item.spend_cop for item in requests if item.response and item.response.review_status == "Aprobado")
    quality_counts = Counter(item.quality_level for item in responses)
    passports = [response_quality_passport(item) for item in responses]
    quality_passports = {item.request_id: response_quality_passport(item) for item in responses}
    validation_by_request = {
        item.request_id: validate_supplier_response(
            item.request,
            method=item.method,
            activity_value=item.activity_value,
            activity_unit=item.activity_unit,
            emission_factor=item.emission_factor,
            factor_unit=item.factor_unit,
            reported_emissions_tco2e=item.reported_emissions_tco2e,
            methodology=item.methodology,
            boundary=item.boundary,
            has_evidence=bool(item.evidence_stored_name),
        )
        for item in responses
    }
    duplicate_counter = Counter(response_duplicate_key(item) for item in approved)
    duplicate_count = sum(count - 1 for count in duplicate_counter.values() if count > 1)
    category = category_from_value(campaign.category)
    return {
        "campaign": campaign,
        "category": category.to_dict() | {"label": canonical_category_label(campaign.category)} if category else None,
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
        "quality_score": round(sum(int(item["score"]) for item in passports) / len(passports)) if passports else 0,
        "quality_passports": quality_passports,
        "validation_by_request": validation_by_request,
        "duplicate_count": duplicate_count,
    }


def scope3_category_matrix(session: Session, inventory: Inventory, summaries: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    assessments = ensure_scope3_assessments(session, inventory.id)
    assessment_by_code = {item.category_code: item for item in assessments}
    if summaries is None:
        campaigns = list(
            session.scalars(
                select(SupplierCampaign)
                .where(SupplierCampaign.inventory_id == inventory.id)
                .options(selectinload(SupplierCampaign.requests).selectinload(SupplierDataRequest.response))
            )
        )
        summaries = [campaign_summary(session, campaign) for campaign in campaigns]
    by_code: dict[str, list[dict[str, object]]] = defaultdict(list)
    for summary in summaries:
        category = summary.get("category")
        if category:
            by_code[str(category["code"])].append(summary)
    matrix: list[dict[str, object]] = []
    for category in SCOPE3_CATEGORIES:
        rows = by_code.get(category.code, [])
        assessment = assessment_by_code[category.code]
        requests = sum(int(item["request_count"]) for item in rows)
        responses = sum(int(item["response_count"]) for item in rows)
        approved = sum(int(item["approved_count"]) for item in rows)
        emissions = round(sum(float(item["emissions"]) for item in rows), 3)
        data_status = "Sin campaña"
        if rows:
            data_status = "Completada" if requests and approved == requests else ("En levantamiento" if requests else "Priorizada")
        matrix.append(
            category.to_dict()
            | {
                "label": f"{category.code} · {category.name}",
                "campaign_count": len(rows),
                "request_count": requests,
                "response_count": responses,
                "approved_count": approved,
                "emissions": emissions,
                "assessment_id": assessment.id,
                "assessment_status": assessment.status,
                "relevance_score": assessment.relevance_score,
                "rationale": assessment.rationale,
                "owner": assessment.owner,
                "data_strategy": assessment.data_strategy,
                "data_status": data_status,
                "status": data_status,
            }
        )
    return matrix


def supply_chain_double_count_warnings(
    session: Session,
    inventory: Inventory,
    matrix: list[dict[str, object]],
) -> list[str]:
    warnings: list[str] = []
    active_codes = {str(item["code"]) for item in matrix if int(item["approved_count"]) > 0}
    manual_sources = list(
        session.scalars(
            select(EmissionSource).where(
                EmissionSource.inventory_id == inventory.id,
                EmissionSource.scope == 3,
                EmissionSource.included.is_(True),
                EmissionSource.category != SUPPLIER_SOURCE_CATEGORY,
            )
        )
    )
    overlaps: set[str] = set()
    for source in manual_sources:
        category = category_from_value(source.category) or category_from_value(source.name)
        if category and category.code in active_codes:
            overlaps.add(f"{category.code} · {category.name}")
    if overlaps:
        warnings.append(
            "Posible doble conteo: existen respuestas aprobadas de proveedores y fuentes manuales incluidas para "
            + ", ".join(sorted(overlaps))
            + ". Reconciliar antes del cierre."
        )
    return warnings


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
    matrix = scope3_category_matrix(session, inventory, summaries)
    active_categories = [item for item in matrix if int(item["campaign_count"]) > 0]
    assessed_categories = [item for item in matrix if item["assessment_status"] != "Pendiente"]
    material_categories = [item for item in matrix if item["assessment_status"] == "Material"]
    approved_categories = [item for item in matrix if int(item["approved_count"]) > 0]
    direction_emissions = {
        direction: round(sum(float(item["emissions"]) for item in matrix if item["direction"] == direction), 3)
        for direction in ("Aguas arriba", "Aguas abajo")
    }
    quality_scores = [int(item["quality_score"]) for item in summaries if int(item["response_count"]) > 0]
    approved_responses = [
        request.response
        for summary in summaries
        for request in summary["requests"]
        if request.response and request.response.review_status == "Aprobado"
    ]
    duplicate_counter = Counter(response_duplicate_key(item) for item in approved_responses)
    duplicate_count = sum(count - 1 for count in duplicate_counter.values() if count > 1)
    warnings = supply_chain_double_count_warnings(session, inventory, matrix)
    conflicting_assessments = [
        item for item in matrix
        if item["assessment_status"] in {"No aplica", "No material"} and int(item["campaign_count"]) > 0
    ]
    if conflicting_assessments:
        warnings.append(
            "Hay categorías clasificadas como no aplicables o no materiales que todavía tienen campañas activas: "
            + ", ".join(str(item["code"]) for item in conflicting_assessments)
            + "."
        )
    material_without_data = [item for item in material_categories if int(item["campaign_count"]) == 0]
    if material_without_data:
        warnings.append(
            "Categorías materiales sin estrategia de levantamiento activa: "
            + ", ".join(str(item["code"]) for item in material_without_data)
            + "."
        )
    if duplicate_count:
        warnings.append(f"Hay {duplicate_count} respuesta(s) aprobada(s) potencialmente duplicada(s) dentro de campañas de proveedores.")
    return {
        "campaigns": summaries,
        "campaign_count": len(campaigns),
        "request_count": sum(int(item["request_count"]) for item in summaries),
        "response_count": sum(int(item["response_count"]) for item in summaries),
        "approved_count": sum(int(item["approved_count"]) for item in summaries),
        "emissions": round(sum(float(item["emissions"]) for item in summaries), 3),
        "spend": sum(float(item["total_spend"]) for item in summaries),
        "response_rate": round(sum(int(item["response_count"]) for item in summaries) / max(sum(int(item["request_count"]) for item in summaries), 1) * 100),
        "spend_coverage": round(
            sum(float(item["total_spend"]) * float(item["spend_coverage"]) / 100 for item in summaries)
            / max(sum(float(item["total_spend"]) for item in summaries), 1)
            * 100
        ),
        "screening_coverage": round(len(assessed_categories) / len(SCOPE3_CATEGORIES) * 100),
        "assessed_category_count": len(assessed_categories),
        "material_category_count": len(material_categories),
        "active_category_count": len(active_categories),
        "approved_category_count": len(approved_categories),
        "quality_score": round(sum(quality_scores) / len(quality_scores)) if quality_scores else 0,
        "duplicate_count": duplicate_count,
        "direction_emissions": direction_emissions,
        "categories": matrix,
        "category_catalog": category_catalog(),
        "warnings": warnings,
        "generated_at": datetime.now(UTC),
    }
