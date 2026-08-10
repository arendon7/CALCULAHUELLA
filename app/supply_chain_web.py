from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import add_audit, get_db
from .db.models import (
    Inventory,
    Scope3CategoryAssessment,
    Supplier,
    SupplierCampaign,
    SupplierDataRequest,
    SupplierResponse,
)
from .scope3_catalog import canonical_category_label, category_from_value
from .security import validate_upload_bytes
from .storage import storage
from .supply_chain import (
    approved_duplicate_responses,
    calculate_supplier_response,
    campaign_summary,
    ensure_scope3_assessments,
    inventory_supply_chain_summary,
    quality_level as supplier_quality_level,
    sync_supplier_source,
    validate_supplier_response,
)


def register_supply_chain_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
    get_inventory,
    ensure_inventory_editable,
    safe_filename,
    allowed_upload_extensions,
    max_upload_size,
) -> None:
    ALLOWED_UPLOAD_EXTENSIONS = allowed_upload_extensions
    MAX_UPLOAD_SIZE = max_upload_size
    @app.get("/cadena-valor", response_class=HTMLResponse)
    def supply_chain_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not (user["can_manage_supply_chain"] or user["can_review"] or user["can_approve"]):
            raise HTTPException(403, "Tu rol no tiene acceso a la cadena de valor")
        inventory = get_inventory(session, user)
        suppliers = list(session.scalars(
            select(Supplier).where(Supplier.organization_id == int(user["organization_id"])).order_by(Supplier.strategic.desc(), Supplier.name)
        ))
        campaigns = list(session.scalars(
            select(SupplierCampaign)
            .where(SupplierCampaign.inventory_id == inventory.id)
            .options(
                selectinload(SupplierCampaign.requests).selectinload(SupplierDataRequest.supplier),
                selectinload(SupplierCampaign.requests).selectinload(SupplierDataRequest.response),
            )
            .order_by(SupplierCampaign.created_at.desc())
        ))
        selected_id = request.query_params.get("campaign_id")
        selected = next((item for item in campaigns if str(item.id) == selected_id), campaigns[0] if campaigns else None)
        selected_summary = campaign_summary(session, selected) if selected else None
        summary = inventory_supply_chain_summary(session, inventory)
        supplier_source = sync_supplier_source(session, inventory.id)
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="supply_chain.html",
            context=common_context(
                request, session, user, "supply_chain", inventory=inventory, suppliers=suppliers,
                campaigns=campaigns, selected=selected, selected_summary=selected_summary,
                supply_summary=summary, supplier_source=supplier_source,
                portal_base=str(request.base_url).rstrip("/"),
            ),
        )

    @app.get("/api/cadena-valor/resumen")
    def supply_chain_summary_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not (user["can_manage_supply_chain"] or user["can_review"] or user["can_approve"]):
            raise HTTPException(403, "Tu rol no tiene acceso a la cadena de valor")
        inventory = get_inventory(session, user)
        summary = inventory_supply_chain_summary(session, inventory)
        session.commit()
        return {
            "inventory_id": inventory.id,
            "campaign_count": summary["campaign_count"],
            "request_count": summary["request_count"],
            "response_count": summary["response_count"],
            "approved_count": summary["approved_count"],
            "emissions_tco2e": summary["emissions"],
            "screening_coverage": summary["screening_coverage"],
            "assessed_category_count": summary["assessed_category_count"],
            "material_category_count": summary["material_category_count"],
            "active_category_count": summary["active_category_count"],
            "approved_category_count": summary["approved_category_count"],
            "quality_score": summary["quality_score"],
            "duplicate_count": summary["duplicate_count"],
            "direction_emissions": summary["direction_emissions"],
            "categories": summary["categories"],
            "warnings": summary["warnings"],
        }

    @app.post("/cadena-valor/categorias/{category_code}/evaluar")
    def assess_scope3_category(
        category_code: str,
        request: Request,
        status: str = Form(...),
        relevance_score: float = Form(0),
        rationale: str = Form(""),
        owner: str = Form("Responsable ambiental"),
        data_strategy: str = Form("Por definir"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_supply_chain")
        inventory = get_inventory(session, user)
        ensure_inventory_editable(inventory)
        category = category_from_value(category_code)
        if not category:
            raise HTTPException(404, "Categoría de Alcance 3 no encontrada")
        allowed_statuses = {"Pendiente", "Material", "No material", "No aplica"}
        if status not in allowed_statuses:
            raise HTTPException(400, "Estado de evaluación no permitido")
        clean_rationale = rationale.strip()
        if status in {"Material", "No material", "No aplica"} and not clean_rationale:
            raise HTTPException(400, "La conclusión de materialidad debe incluir una justificación.")
        ensure_scope3_assessments(session, inventory.id)
        assessment = session.scalar(
            select(Scope3CategoryAssessment).where(
                Scope3CategoryAssessment.inventory_id == inventory.id,
                Scope3CategoryAssessment.category_code == category.code,
            )
        )
        if not assessment:
            raise HTTPException(404, "Evaluación de categoría no disponible")
        assessment.status = status
        assessment.relevance_score = min(5.0, max(0.0, relevance_score))
        assessment.rationale = clean_rationale
        assessment.owner = owner.strip() or "Responsable ambiental"
        assessment.data_strategy = data_strategy.strip() or "Por definir"
        assessment.updated_by = str(user["email"])
        assessment.updated_at = datetime.now(UTC)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "EVALUAR",
            "Categoría Scope 3",
            f"{category.code} · {category.name}",
            f"{status}; relevancia {assessment.relevance_score:.1f}/5",
        )
        session.commit()
        set_flash(request, f"{category.code} actualizada como {status.lower()}.")
        return RedirectResponse("/cadena-valor", status_code=303)


    @app.post("/cadena-valor/proveedores/nuevo")
    def create_supplier(
        request: Request, name: str = Form(...), tax_id: str = Form(""), sector: str = Form(""), country: str = Form("Colombia"),
        contact_name: str = Form(""), contact_email: str = Form(""), annual_spend_cop: float = Form(0),
        strategic: str | None = Form(None), risk_level: str = Form("Medio"),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_supply_chain")
        supplier = Supplier(
            organization_id=int(user["organization_id"]), name=name.strip(), tax_id=tax_id.strip(), sector=sector.strip(),
            country=country.strip(), contact_name=contact_name.strip(), contact_email=contact_email.strip().lower(),
            annual_spend_cop=max(0, annual_spend_cop), strategic=strategic is not None, risk_level=risk_level,
        )
        session.add(supplier)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Proveedor", supplier.name, f"Sector {supplier.sector}")
        session.commit()
        set_flash(request, "Proveedor registrado en la cadena de valor.")
        return RedirectResponse("/cadena-valor", status_code=303)

    @app.post("/cadena-valor/campanas/nueva")
    def create_supplier_campaign(
        request: Request, inventory_id: int = Form(...), name: str = Form(...), category: str = Form("Bienes y servicios adquiridos"),
        due_date: str = Form(...), methodology: str = Form("GHG Protocol Scope 3"), description: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_supply_chain")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        canonical_category = canonical_category_label(category)
        campaign = SupplierCampaign(
            inventory_id=inventory.id, name=name.strip(), category=canonical_category, due_date=parse_date(due_date),
            status="Borrador", methodology=methodology.strip(), description=description.strip(), created_by=str(user["email"]),
        )
        session.add(campaign)
        ensure_scope3_assessments(session, inventory.id)
        category_profile = category_from_value(campaign.category)
        if category_profile:
            assessment = session.scalar(select(Scope3CategoryAssessment).where(
                Scope3CategoryAssessment.inventory_id == inventory.id,
                Scope3CategoryAssessment.category_code == category_profile.code,
            ))
            if assessment:
                assessment.status = "Material"
                assessment.relevance_score = max(assessment.relevance_score, 4)
                assessment.rationale = assessment.rationale or "Categoría priorizada mediante campaña de levantamiento."
                assessment.data_strategy = "Campaña de proveedores"
                assessment.updated_by = str(user["email"])
                assessment.updated_at = datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Campaña de proveedores", campaign.name, campaign.category)
        session.commit()
        set_flash(request, "Campaña creada. Ahora agrega solicitudes a proveedores.")
        return RedirectResponse(f"/cadena-valor?campaign_id={campaign.id}", status_code=303)

    @app.post("/cadena-valor/solicitudes/nueva")
    def create_supplier_request(
        request: Request, campaign_id: int = Form(...), supplier_id: int = Form(...), product_service: str = Form(...),
        quantity: float = Form(0), unit: str = Form("unidad"), spend_cop: float = Form(0),
        requested_method: str = Form("Factor específico del proveedor"), due_date: str = Form(...), notes: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_supply_chain")
        campaign = session.scalar(
            select(SupplierCampaign).join(Inventory).where(
                SupplierCampaign.id == campaign_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        supplier = session.scalar(select(Supplier).where(Supplier.id == supplier_id, Supplier.organization_id == int(user["organization_id"])))
        if not campaign or not supplier:
            raise HTTPException(404, "Campaña o proveedor no encontrado")
        ensure_inventory_editable(campaign.inventory)
        token = secrets.token_urlsafe(24)
        data_request = SupplierDataRequest(
            campaign_id=campaign.id, supplier_id=supplier.id, product_service=product_service.strip(),
            quantity=max(0, quantity), unit=unit.strip(), spend_cop=max(0, spend_cop), requested_method=requested_method,
            status="Enviada", due_date=parse_date(due_date), access_token=token,
            token_expires_at=datetime.combine(parse_date(due_date), datetime.max.time(), tzinfo=UTC), sent_at=datetime.now(UTC), notes=notes.strip(),
        )
        campaign.status = "En curso"
        session.add(data_request)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "SOLICITAR", "Dato de proveedor", supplier.name, product_service)
        session.commit()
        set_flash(request, "Solicitud creada. El enlace seguro está disponible en la tabla de la campaña.")
        return RedirectResponse(f"/cadena-valor?campaign_id={campaign.id}", status_code=303)

    @app.post("/cadena-valor/solicitudes/{request_id}/renovar")
    def renew_supplier_token(
        request_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_supply_chain")
        data_request = session.scalar(
            select(SupplierDataRequest).join(SupplierCampaign).join(Inventory).where(
                SupplierDataRequest.id == request_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not data_request:
            raise HTTPException(404, "Solicitud no encontrada")
        data_request.access_token = secrets.token_urlsafe(24)
        data_request.token_expires_at = datetime.combine(data_request.due_date, datetime.max.time(), tzinfo=UTC)
        data_request.sent_at = datetime.now(UTC)
        data_request.status = "Enviada"
        session.commit()
        set_flash(request, "Enlace seguro renovado.")
        return RedirectResponse(f"/cadena-valor?campaign_id={data_request.campaign_id}", status_code=303)

    @app.get("/proveedor/responder/{token}", response_class=HTMLResponse)
    def supplier_public_portal(token: str, request: Request, session: Session = Depends(get_db)):
        data_request = session.scalar(
            select(SupplierDataRequest)
            .where(SupplierDataRequest.access_token == token)
            .options(
                selectinload(SupplierDataRequest.supplier),
                selectinload(SupplierDataRequest.campaign).selectinload(SupplierCampaign.inventory).selectinload(Inventory.organization),
                selectinload(SupplierDataRequest.response),
            )
        )
        if not data_request:
            raise HTTPException(404, "Enlace de proveedor no encontrado")
        expires = data_request.token_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        expired = bool(expires and expires < datetime.now(UTC))
        return templates.TemplateResponse(
            request=request, name="supplier_portal.html",
            context={"data_request": data_request, "expired": expired, "flash": request.session.pop("supplier_flash", None)},
        )

    @app.post("/proveedor/responder/{token}")
    async def submit_supplier_response(
        token: str, request: Request, method: str = Form(...), activity_value: float = Form(0), activity_unit: str = Form(""),
        emission_factor: float = Form(0), factor_unit: str = Form("kg CO2e/unidad"), reported_emissions_tco2e: float = Form(0),
        methodology: str = Form(""), boundary: str = Form(""), verified: str | None = Form(None), notes: str = Form(""),
        evidence: UploadFile | None = File(None), session: Session = Depends(get_db),
    ):
        data_request = session.scalar(
            select(SupplierDataRequest)
            .where(SupplierDataRequest.access_token == token)
            .options(selectinload(SupplierDataRequest.supplier), selectinload(SupplierDataRequest.campaign), selectinload(SupplierDataRequest.response))
        )
        if not data_request:
            raise HTTPException(404, "Enlace de proveedor no encontrado")
        expires = data_request.token_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires and expires < datetime.now(UTC):
            raise HTTPException(410, "El enlace de respuesta venció")
        existing_evidence = bool(data_request.response and data_request.response.evidence_stored_name)
        validation = validate_supplier_response(
            data_request,
            method=method,
            activity_value=max(0, activity_value),
            activity_unit=activity_unit.strip() or data_request.unit,
            emission_factor=max(0, emission_factor),
            factor_unit=factor_unit.strip(),
            reported_emissions_tco2e=max(0, reported_emissions_tco2e),
            methodology=methodology.strip(),
            boundary=boundary.strip(),
            has_evidence=existing_evidence or bool(evidence and evidence.filename),
        )
        if validation["errors"]:
            raise HTTPException(400, " ".join(validation["errors"]))
        file_name = ""
        stored_name = ""
        sha256 = ""
        file_size = 0
        if evidence and evidence.filename:
            extension = Path(evidence.filename).suffix.lower()
            if extension not in ALLOWED_UPLOAD_EXTENSIONS:
                raise HTTPException(400, "Formato de evidencia no permitido")
            content = await evidence.read(MAX_UPLOAD_SIZE + 1)
            if len(content) > MAX_UPLOAD_SIZE:
                raise HTTPException(400, f"El archivo supera el límite de {settings.max_upload_mb} MB")
            file_name = safe_filename(evidence.filename)
            valid_file, validation_message, detected_mime = validate_upload_bytes(
                file_name, content, evidence.content_type, ALLOWED_UPLOAD_EXTENSIONS
            )
            if not valid_file:
                raise HTTPException(400, validation_message)
            stored_name = f"uploads/supplier_portal/request_{data_request.id}/{datetime.now(UTC):%Y%m%d%H%M%S}_{file_name}"
            storage.put_bytes(stored_name, content, detected_mime)
            sha256 = hashlib.sha256(content).hexdigest()
            file_size = len(content)
        calculated = calculate_supplier_response(
            data_request, method=method, activity_value=max(0, activity_value), emission_factor=max(0, emission_factor),
            reported_emissions_tco2e=max(0, reported_emissions_tco2e),
        )
        has_evidence = bool(stored_name or (data_request.response and data_request.response.evidence_stored_name))
        level = supplier_quality_level(method, verified is not None, has_evidence)
        response = data_request.response or SupplierResponse(request_id=data_request.id)
        response.method = method
        response.activity_value = max(0, activity_value)
        response.activity_unit = activity_unit.strip() or data_request.unit
        response.emission_factor = max(0, emission_factor)
        response.factor_unit = factor_unit.strip()
        response.reported_emissions_tco2e = max(0, reported_emissions_tco2e)
        response.calculated_emissions_tco2e = calculated
        response.methodology = methodology.strip()
        response.boundary = boundary.strip()
        response.verified = verified is not None
        response.quality_level = level
        response.notes = notes.strip()
        response.review_status = "Pendiente"
        response.submitted_at = datetime.now(UTC)
        if stored_name:
            response.evidence_name = file_name
            response.evidence_stored_name = stored_name
            response.evidence_sha256 = sha256
            response.evidence_size = file_size
        session.add(response)
        data_request.status = "Respondida"
        data_request.responded_at = datetime.now(UTC)
        session.commit()
        warning_suffix = "" if not validation["warnings"] else f" Observaciones automáticas: {len(validation['warnings'])}."
        request.session["supplier_flash"] = {"message": "Respuesta recibida. La empresa revisará la metodología y el soporte." + warning_suffix, "level": "success"}
        return RedirectResponse(f"/proveedor/responder/{token}", status_code=303)

    @app.post("/cadena-valor/respuestas/{response_id}/revisar")
    def review_supplier_response(
        response_id: int, request: Request, decision: str = Form(...), reviewer_comments: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        if not (user["can_review"] or user["can_manage_supply_chain"]):
            raise HTTPException(403, "Tu rol no puede revisar respuestas de proveedores")
        response = session.scalar(
            select(SupplierResponse)
            .join(SupplierDataRequest).join(SupplierCampaign).join(Inventory)
            .where(SupplierResponse.id == response_id, Inventory.organization_id == int(user["organization_id"]))
            .options(selectinload(SupplierResponse.request).selectinload(SupplierDataRequest.campaign))
        )
        if not response:
            raise HTTPException(404, "Respuesta no encontrada")
        if decision == "Aprobado":
            validation = validate_supplier_response(
                response.request,
                method=response.method,
                activity_value=response.activity_value,
                activity_unit=response.activity_unit,
                emission_factor=response.emission_factor,
                factor_unit=response.factor_unit,
                reported_emissions_tco2e=response.reported_emissions_tco2e,
                methodology=response.methodology,
                boundary=response.boundary,
                has_evidence=bool(response.evidence_stored_name),
            )
            blockers = list(validation["errors"])
            if not response.methodology.strip():
                blockers.append("La metodología debe documentarse antes de aprobar.")
            if not response.boundary.strip():
                blockers.append("Los límites del cálculo deben documentarse antes de aprobar.")
            duplicates = approved_duplicate_responses(session, response)
            if duplicates:
                blockers.append("Existe otra respuesta aprobada para la misma categoría, proveedor y producto o servicio.")
            if blockers:
                raise HTTPException(409, " ".join(blockers))
        response.review_status = decision
        response.reviewer_comments = reviewer_comments.strip()
        response.reviewed_by = str(user["email"])
        response.reviewed_at = datetime.now(UTC)
        response.request.status = "Aprobada" if decision == "Aprobado" else "Devuelta"
        session.flush()
        source = sync_supplier_source(session, response.request.campaign.inventory_id)
        add_audit(session, int(user["organization_id"]), str(user["email"]), decision.upper(), "Respuesta de proveedor", response.request.supplier.name, f"{response.calculated_emissions_tco2e:.3f} tCO2e")
        session.commit()
        set_flash(request, f"Respuesta {decision.lower()}. La fuente de alcance 3 quedó en {source.emissions:.3f} tCO₂e.")
        return RedirectResponse(f"/cadena-valor?campaign_id={response.request.campaign_id}", status_code=303)

    @app.get("/cadena-valor/respuestas/{response_id}/evidencia")
    def download_supplier_evidence(
        response_id: int, session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        response = session.scalar(
            select(SupplierResponse).join(SupplierDataRequest).join(SupplierCampaign).join(Inventory).where(
                SupplierResponse.id == response_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not response or not response.evidence_stored_name:
            raise HTTPException(404, "Evidencia no disponible")
        if not storage.exists(response.evidence_stored_name):
            raise HTTPException(404, "Archivo no encontrado")
        local_path = storage.local_path(response.evidence_stored_name)
        if local_path:
            return FileResponse(local_path, filename=response.evidence_name or local_path.name)
        return RedirectResponse(storage.presigned_url(response.evidence_stored_name), status_code=302)

    @app.get("/cadena-valor/plantilla.xlsx")
    def supplier_campaign_template(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not (user["can_manage_supply_chain"] or user["can_review"]):
            raise HTTPException(403)
        inventory = get_inventory(session, user)
        wb = Workbook()
        ws = wb.active
        ws.title = "Solicitudes proveedores"
        ws.append([
            "Código categoría", "Categoría Scope 3", "Dirección", "Proveedor", "NIT", "Producto o servicio",
            "Cantidad", "Unidad", "Gasto COP", "Método solicitado", "Estado", "Fecha límite", "Método respondido",
            "Calidad A-D", "Revisión", "Emisiones tCO2e", "Metodología", "Límite", "Enlace seguro",
        ])
        requests = session.scalars(
            select(SupplierDataRequest)
            .join(SupplierCampaign).where(SupplierCampaign.inventory_id == inventory.id)
            .options(
                selectinload(SupplierDataRequest.supplier),
                selectinload(SupplierDataRequest.campaign),
                selectinload(SupplierDataRequest.response),
            )
            .order_by(SupplierDataRequest.id)
        )
        base = str(request.base_url).rstrip("/") + "/proveedor/responder/"
        for item in requests:
            category = category_from_value(item.campaign.category)
            response = item.response
            ws.append([
                category.code if category else "", category.name if category else item.campaign.category,
                category.direction if category else "", item.supplier.name, item.supplier.tax_id, item.product_service,
                item.quantity, item.unit, item.spend_cop, item.requested_method, item.status, item.due_date,
                response.method if response else "", response.quality_level if response else "",
                response.review_status if response else "", response.calculated_emissions_tco2e if response else 0,
                response.methodology if response else "", response.boundary if response else "", base + item.access_token,
            ])
        summary = inventory_supply_chain_summary(session, inventory)
        categories_ws = wb.create_sheet("Screening 15 categorías")
        categories_ws.append(["Código", "Categoría", "Dirección", "Evaluación", "Relevancia 0-5", "Justificación", "Responsable", "Estrategia de datos", "Estado de datos", "Campañas", "Solicitudes", "Respuestas", "Aprobadas", "Emisiones tCO2e", "Límite mínimo", "Métodos recomendados"])
        for category in summary["categories"]:
            categories_ws.append([
                category["code"], category["name"], category["direction"], category["assessment_status"],
                category["relevance_score"], category["rationale"], category["owner"], category["data_strategy"],
                category["data_status"], category["campaign_count"], category["request_count"], category["response_count"],
                category["approved_count"], category["emissions"], category["minimum_boundary"], ", ".join(category["recommended_methods"]),
            ])
        stream = BytesIO()
        wb.save(stream)
        return Response(stream.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=cadena_valor_proveedores.xlsx"})
