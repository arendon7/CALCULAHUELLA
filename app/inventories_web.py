from __future__ import annotations

from datetime import UTC, date, datetime
import json

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .calculations import convert_value, recalculate_source, source_calculation_summary
from .database import (
    ActivityData,
    ActivityFactorSelection,
    EmissionCalculation,
    EmissionFactor,
    EmissionFactorVersion,
    EmissionSource,
    Facility,
    Inventory,
    InventoryFacility,
    SourceFactorAssignment,
    add_audit,
    get_db,
)
from .inventory_starters import add_starter_sources, starter_pack_catalog
from .factor_advisor import advise_factor, conversation_for_record
from .repositories.inventories import list_inventories as list_inventory_records
from .repositories.organizations import list_active_facilities
from .services.inventories import create_inventory as create_inventory_record
from .service_operations import ensure_capacity


def register_inventory_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
    get_inventory,
    get_source_for_user,
    ensure_inventory_editable,
    inventory_metrics,
    allowed_units,
    data_origins,
) -> None:
    ALLOWED_UNITS = allowed_units
    DATA_ORIGINS = data_origins
    @app.get("/inventarios", response_class=HTMLResponse)
    def inventories_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventories = list_inventory_records(session, int(user["organization_id"]))
        return templates.TemplateResponse(
            request=request,
            name="inventories.html",
            context=common_context(request, session, user, "inventories", inventories=inventories),
        )


    @app.get("/inventarios/nuevo", response_class=HTMLResponse)
    def inventory_new_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_inventory")
        facilities = list_active_facilities(session, int(user["organization_id"]))
        current_year = date.today().year
        return templates.TemplateResponse(
            request=request,
            name="inventory_form.html",
            context=common_context(
                request,
                session,
                user,
                "inventories",
                inventory=None,
                facilities=facilities,
                selected_facilities=[],
                starter_packs=starter_pack_catalog(),
                default_year=current_year,
                default_start=f"{current_year}-01-01",
                default_end=f"{current_year}-12-31",
            ),
        )


    @app.post("/inventarios/nuevo")
    def inventory_create(
        request: Request,
        name: str = Form(...),
        start_date: str = Form(...),
        end_date: str = Form(...),
        objective: str = Form(...),
        base_year: int = Form(...),
        methodology: str = Form(...),
        methodology_version: str = Form(...),
        gwp_version: str = Form(...),
        consolidation_approach: str = Form(...),
        materiality_threshold: float = Form(5),
        notes: str = Form(""),
        facility_ids: list[int] = Form(default=[]),
        starter_pack: str = Form("custom"),
        source_responsible: str = Form("Responsable ambiental"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        ensure_capacity(session, int(user["organization_id"]), "inventories", 1)
        start = parse_date(start_date)
        end = parse_date(end_date)
        if end < start:
            raise HTTPException(400, "El periodo final no puede ser anterior al inicial")
        inventory = create_inventory_record(
            session,
            int(user["organization_id"]),
            actor_email=str(user["email"]),
            name=name,
            start_date=start,
            end_date=end,
            objective=objective,
            base_year=base_year,
            methodology=methodology,
            methodology_version=methodology_version,
            gwp_version=gwp_version,
            consolidation_approach=consolidation_approach,
            materiality_threshold=materiality_threshold,
            notes=notes,
            facility_ids=facility_ids,
        )
        primary_facility = None
        if facility_ids:
            primary_facility = session.scalar(
                select(Facility)
                .where(Facility.organization_id == int(user["organization_id"]), Facility.id.in_(facility_ids))
                .order_by(Facility.id)
            )
        created_sources = add_starter_sources(
            session,
            inventory,
            pack_code=starter_pack,
            responsible=source_responsible,
            actor_email=str(user["email"]),
            facility_id=primary_facility.id if primary_facility else None,
        )
        session.commit()
        if created_sources:
            set_flash(request, f"Inventario creado con {len(created_sources)} fuentes iniciales. Confírmalas antes de cargar datos.")
        else:
            set_flash(request, "El inventario fue creado. Agrega o selecciona las fuentes que correspondan a la operación.")
        return RedirectResponse(f"/inventarios/{inventory.id}/fuentes", status_code=303)


    @app.get("/inventario")
    def inventory_alias(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        return RedirectResponse(f"/inventarios/{inventory.id}", status_code=303)


    @app.get("/inventarios/{inventory_id}", response_class=HTMLResponse)
    def inventory_page(inventory_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user, inventory_id)
        metrics = inventory_metrics(inventory)
        return templates.TemplateResponse(
            request=request,
            name="inventory.html",
            context=common_context(request, session, user, "inventories", inventory=inventory, sources=inventory.sources, **metrics),
        )


    @app.get("/inventarios/{inventory_id}/editar", response_class=HTMLResponse)
    def inventory_edit_page(inventory_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        facilities = list_active_facilities(session, int(user["organization_id"]))
        selected_facilities = [link.facility_id for link in inventory.facility_links if link.included]
        return templates.TemplateResponse(
            request=request,
            name="inventory_form.html",
            context=common_context(
                request,
                session,
                user,
                "inventories",
                inventory=inventory,
                facilities=facilities,
                selected_facilities=selected_facilities,
                starter_packs=starter_pack_catalog(),
                default_year=inventory.base_year,
                default_start=inventory.start_date.isoformat(),
                default_end=inventory.end_date.isoformat(),
            ),
        )


    @app.post("/inventarios/{inventory_id}/editar")
    def inventory_edit(
        inventory_id: int,
        request: Request,
        name: str = Form(...),
        start_date: str = Form(...),
        end_date: str = Form(...),
        objective: str = Form(...),
        base_year: int = Form(...),
        methodology: str = Form(...),
        methodology_version: str = Form(...),
        gwp_version: str = Form(...),
        consolidation_approach: str = Form(...),
        materiality_threshold: float = Form(5),
        status: str = Form("Borrador"),
        current_stage: str = Form("Configuración"),
        notes: str = Form(""),
        facility_ids: list[int] = Form(default=[]),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        parsed_start = parse_date(start_date)
        parsed_end = parse_date(end_date)
        if parsed_end < parsed_start:
            raise HTTPException(400, "El periodo final no puede ser anterior al inicial")
        inventory.name = name.strip()
        inventory.start_date = parsed_start
        inventory.end_date = parsed_end
        inventory.objective = objective.strip()
        inventory.base_year = base_year
        inventory.methodology = methodology.strip()
        inventory.methodology_version = methodology_version.strip()
        inventory.gwp_version = gwp_version.strip()
        inventory.consolidation_approach = consolidation_approach.strip()
        inventory.materiality_threshold = max(materiality_threshold, 0)
        protected_statuses = {"En revisión", "Pendiente de aprobación", "Aprobado", "Cerrado"}
        if status.strip() in protected_statuses:
            raise HTTPException(400, "Ese estado solo puede asignarse desde el flujo formal de revisión y aprobación")
        inventory.status = status.strip()
        inventory.current_stage = current_stage.strip()
        inventory.notes = notes.strip()

        for link in inventory.facility_links:
            link.included = link.facility_id in facility_ids
        existing_ids = {link.facility_id for link in inventory.facility_links}
        for facility_id in facility_ids:
            if facility_id not in existing_ids:
                facility = session.get(Facility, facility_id)
                if facility and facility.organization_id == int(user["organization_id"]):
                    session.add(InventoryFacility(inventory_id=inventory.id, facility_id=facility.id, included=True, inclusion_percentage=100))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Inventario", inventory.name, "Actualización de configuración metodológica y límites")
        session.commit()
        set_flash(request, "La configuración del inventario fue actualizada.")
        return RedirectResponse(f"/inventarios/{inventory.id}", status_code=303)


    @app.get("/inventarios/{inventory_id}/fuentes", response_class=HTMLResponse)
    def sources_page(inventory_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user, inventory_id)
        facilities = [link.facility for link in inventory.facility_links if link.included]
        records_count = sum(len(source.activity_records) for source in inventory.sources)
        return templates.TemplateResponse(
            request=request,
            name="sources.html",
            context=common_context(
                request,
                session,
                user,
                "sources",
                inventory=inventory,
                sources=inventory.sources,
                facilities=facilities,
                starter_packs=starter_pack_catalog(),
                records_count=records_count,
            ),
        )


    @app.post("/inventarios/{inventory_id}/fuentes/paquete")
    def source_pack_add(
        inventory_id: int,
        request: Request,
        pack_code: str = Form(...),
        responsible: str = Form("Responsable ambiental"),
        facility_id: int | None = Form(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_sources")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        facility = session.get(Facility, facility_id) if facility_id else None
        if facility and facility.organization_id != int(user["organization_id"]):
            raise HTTPException(400, "Sede inválida")
        included_facility_ids = {link.facility_id for link in inventory.facility_links if link.included}
        if facility and facility.id not in included_facility_ids:
            raise HTTPException(400, "La sede debe estar incluida en el inventario")
        created = add_starter_sources(
            session,
            inventory,
            pack_code=pack_code,
            responsible=responsible,
            actor_email=str(user["email"]),
            facility_id=facility.id if facility else None,
        )
        session.commit()
        if created:
            set_flash(request, f"Se agregaron {len(created)} fuentes sin duplicar las existentes.")
        else:
            set_flash(request, "El paquete ya estaba cubierto o no corresponde a una opción disponible.", "error")
        return RedirectResponse(f"/inventarios/{inventory.id}/fuentes", status_code=303)


    @app.post("/inventarios/{inventory_id}/fuentes/nueva")
    def source_create(
        inventory_id: int,
        request: Request,
        name: str = Form(...),
        scope: int = Form(...),
        category: str = Form(...),
        facility_id: int | None = Form(None),
        responsible: str = Form(...),
        materiality: str = Form("Media"),
        data_frequency: str = Form("Mensual"),
        preferred_unit: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_sources")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        facility = session.get(Facility, facility_id) if facility_id else None
        if facility and facility.organization_id != int(user["organization_id"]):
            raise HTTPException(400, "Sede inválida")
        included_facility_ids = {link.facility_id for link in inventory.facility_links if link.included}
        if facility and facility.id not in included_facility_ids:
            raise HTTPException(400, "La sede debe estar incluida en el inventario")
        normalized_name = name.strip()
        if any(item.name.strip().casefold() == normalized_name.casefold() for item in inventory.sources):
            set_flash(request, "Ya existe una fuente con ese nombre en el inventario.", "error")
            return RedirectResponse(f"/inventarios/{inventory.id}/fuentes", status_code=303)
        normalized_unit = preferred_unit.strip()
        if normalized_unit and normalized_unit not in ALLOWED_UNITS:
            raise HTTPException(400, "Unidad esperada no autorizada")
        source = EmissionSource(
            inventory_id=inventory.id,
            facility_id=facility.id if facility else None,
            name=normalized_name,
            scope=max(1, min(scope, 3)),
            category=category.strip(),
            responsible=responsible.strip() or "Responsable ambiental",
            materiality=materiality if materiality in {"Alta", "Media", "Baja"} else "Media",
            data_frequency=data_frequency if data_frequency in {"Mensual", "Trimestral", "Anual", "Por evento"} else "Mensual",
            preferred_unit=normalized_unit or {"Electricidad": "kWh", "Diésel": "L", "Vehículos": "L", "Refrigerantes": "kg", "Residuos": "t", "Transporte contratado": "t·km"}.get(normalized_name, ""),
            progress=0,
            status="Pendiente",
            emissions=0,
            icon="activity",
        )
        session.add(source)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Fuente", source.name, f"Alcance {source.scope} · {source.category}")
        session.commit()
        set_flash(request, "La fuente fue agregada al inventario.")
        return RedirectResponse(f"/inventarios/{inventory.id}/fuentes", status_code=303)


    @app.get("/fuentes/{source_id}", response_class=HTMLResponse)
    def source_detail(source_id: int, request: Request, activity_data_id: int | None = None, show_all: bool = False, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        source = session.scalar(
            select(EmissionSource)
            .where(EmissionSource.id == source_id)
            .options(
                selectinload(EmissionSource.inventory),
                selectinload(EmissionSource.facility),
                selectinload(EmissionSource.activity_records).selectinload(ActivityData.evidence),
                selectinload(EmissionSource.activity_records).selectinload(ActivityData.factor_selections).selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.activity_records).selectinload(ActivityData.factor_selections).selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.gas),
                selectinload(EmissionSource.activity_records).selectinload(ActivityData.calculations).selectinload(EmissionCalculation.factor_version).selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.evidence_documents),
                selectinload(EmissionSource.factor_assignments).selectinload(SourceFactorAssignment.factor_version).selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionSource.factor_assignments).selectinload(SourceFactorAssignment.factor_version).selectinload(EmissionFactorVersion.gas),
            )
        )
        if not source or source.inventory.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Fuente no encontrada")
        records = sorted(source.activity_records, key=lambda item: (item.period_start, item.id))
        record_total = len(records)
        display_records = records if show_all else records[-12:]
        selected_record = next((item for item in records if item.id == activity_data_id), None)
        conversation_records = [selected_record] if selected_record else records[-1:]
        total_activity = round(sum(item.value for item in records), 6)
        quality_counts = {level: sum(1 for item in records if item.quality_level == level) for level in ("A", "B", "C", "D")}
        primary_quality = max(quality_counts, key=quality_counts.get) if records else "Sin datos"
        summary = source_calculation_summary(session, source.id)
        available_versions = list(
            session.scalars(
                select(EmissionFactorVersion)
                .where(EmissionFactorVersion.status == "Aprobado")
                .options(selectinload(EmissionFactorVersion.factor), selectinload(EmissionFactorVersion.gas))
                .order_by(EmissionFactor.activity_type, EmissionFactor.name)
                .join(EmissionFactor)
            )
        )
        factor_catalog = list(available_versions)
        assigned_ids = {item.factor_version_id for item in source.factor_assignments if item.active}
        available_versions = [item for item in available_versions if item.id not in assigned_ids]
        factor_conversations = [conversation_for_record(session, source, record, factor_catalog) for record in conversation_records]
        conversion_examples = []
        for record in records[:3]:
            for assignment in source.factor_assignments[:1]:
                normalized, note = convert_value(session, record.value, record.unit, assignment.factor_version.input_unit)
                conversion_examples.append({"record": record, "normalized": normalized, "note": note})
        calculation = {
            "activity": total_activity,
            "activity_unit": source.preferred_unit or (records[0].unit if records else ""),
            "conversion": conversion_examples[0]["note"] if conversion_examples else "Sin datos o factores asignados.",
            "formula": "Dato normalizado × factor de emisión × GWP",
            "result": source.emissions,
            "quality": primary_quality,
        }
        return templates.TemplateResponse(
            request=request,
            name="source.html",
            context=common_context(
                request,
                session,
                user,
                "sources",
                inventory=source.inventory,
                source=source,
                calculation=calculation,
                records=display_records,
                all_records=records,
                record_total=record_total,
                show_all=show_all,
                selected_activity_data_id=selected_record.id if selected_record else None,
                documents=source.evidence_documents,
                total_activity=total_activity,
                quality_counts=quality_counts,
                allowed_units=ALLOWED_UNITS,
                data_origins=DATA_ORIGINS,
                summary=summary,
                available_versions=available_versions,
                assignments=[item for item in source.factor_assignments if item.active],
                conversion_examples=conversion_examples,
                factor_conversations=factor_conversations,
                facilities=list_active_facilities(session, int(user["organization_id"])),
            ),
        )


    @app.post("/fuentes/{source_id}/datos/{activity_data_id}/factores/seleccionar")
    def select_factor_for_record(
        source_id: int,
        activity_data_id: int,
        request: Request,
        factor_version_id: int = Form(...),
        rationale: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id).options(selectinload(EmissionSource.inventory)))
        record = session.get(ActivityData, activity_data_id)
        factor = session.scalar(select(EmissionFactorVersion).where(EmissionFactorVersion.id == factor_version_id).options(selectinload(EmissionFactorVersion.factor), selectinload(EmissionFactorVersion.gas)))
        if not source or source.inventory.organization_id != int(user["organization_id"]) or not record or record.source_id != source.id:
            raise HTTPException(404, "Dato o fuente no encontrados")
        if not factor or factor.status != "Aprobado":
            raise HTTPException(400, "Solo pueden proponerse factores aprobados")
        advice = advise_factor(session, source, record, factor)
        if not advice["calculable"]:
            set_flash(request, "El factor no puede proponerse: no existe una conversión aprobada entre las unidades.", "error")
            return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)
        normalized_rationale = rationale.strip()
        if len(normalized_rationale) < 12:
            set_flash(request, "Documenta brevemente por qué el factor representa este dato.", "error")
            return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)
        selection = session.scalar(select(ActivityFactorSelection).where(
            ActivityFactorSelection.activity_data_id == record.id,
            ActivityFactorSelection.factor_version_id == factor.id,
        ))
        documentation = advice.get("documentation")
        snapshot = json.dumps({
            "compatibility_score": advice["score"],
            "breakdown": advice["breakdown"],
            "blockers": advice["blockers"],
            "hard_blockers": advice.get("hard_blockers", []),
            "record": {"value": record.value, "unit": record.unit, "period_start": record.period_start.isoformat(), "period_end": record.period_end.isoformat()},
            "factor": {"id": factor.id, "name": factor.factor.name, "version": factor.version, "input_unit": factor.input_unit, "output_unit": factor.output_unit, "gas": factor.gas.code},
            "documentation": {
                "reporting_use": documentation.reporting_use if documentation else "Sin clasificar",
                "quality_grade": documentation.quality_grade if documentation else "N/A",
                "review_status": documentation.review_status if documentation else "Sin documentación",
                "data_year": documentation.data_year if documentation else None,
            },
        }, ensure_ascii=False)
        if selection:
            selection.active = True
            selection.compatibility_score = int(advice["score"])
            selection.rationale = normalized_rationale
            selection.selection_status = "Propuesto"
            selection.selected_by = str(user["email"])
            selection.selected_at = datetime.now(UTC)
            selection.reviewed_by = ""
            selection.reviewed_at = None
            selection.review_notes = ""
            selection.decision_snapshot = snapshot
            selection.applied_at = None
        else:
            selection = ActivityFactorSelection(
                activity_data_id=record.id, factor_version_id=factor.id, active=True,
                compatibility_score=int(advice["score"]), selection_status="Propuesto",
                rationale=normalized_rationale, selected_by=str(user["email"]),
                decision_snapshot=snapshot,
            )
            session.add(selection)
        session.flush()
        recalculate_source(session, source)
        add_audit(
            session, int(user["organization_id"]), str(user["email"]), "PROPONER",
            "Factor por dato", f"Dato {record.id} · {factor.factor.name}",
            detail=f"Compatibilidad {advice['score']}% · {normalized_rationale}",
        )
        session.commit()
        set_flash(request, "Factor propuesto. Debe aprobarse antes de reemplazar los factores heredados en el cálculo.")
        return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)


    @app.post("/fuentes/{source_id}/datos/{activity_data_id}/factores/{selection_id}/revisar")
    def review_factor_for_record(
        source_id: int,
        activity_data_id: int,
        selection_id: int,
        request: Request,
        decision: str = Form(...),
        review_notes: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not (user.get("can_review") or user.get("can_approve")):
            raise HTTPException(403, "Tu rol no puede revisar decisiones metodológicas")
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id).options(selectinload(EmissionSource.inventory)))
        record = session.get(ActivityData, activity_data_id)
        selection = session.scalar(select(ActivityFactorSelection).where(
            ActivityFactorSelection.id == selection_id,
            ActivityFactorSelection.activity_data_id == activity_data_id,
        ).options(
            selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.factor),
            selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.gas),
        ))
        if not source or source.inventory.organization_id != int(user["organization_id"]) or not record or record.source_id != source.id or not selection:
            raise HTTPException(404, "Selección no encontrada")
        normalized_notes = review_notes.strip()
        if len(normalized_notes) < 8:
            set_flash(request, "La revisión debe explicar brevemente el criterio aplicado.", "error")
            return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)
        decision_map = {"Aprobar": "Aprobado", "Requiere ajuste": "Requiere ajuste", "Rechazar": "Rechazado"}
        if decision not in decision_map:
            raise HTTPException(400, "Decisión no válida")
        advice = advise_factor(session, source, record, selection.factor_version)
        if decision == "Aprobar" and not advice["calculable"]:
            set_flash(request, "No puede aprobarse una selección sin conversión de unidades válida.", "error")
            return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)
        if decision == "Aprobar" and advice.get("hard_blockers"):
            set_flash(request, "La selección no puede aprobarse mientras existan bloqueadores metodológicos: " + " ".join(advice["hard_blockers"]), "error")
            return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)
        selection.selection_status = decision_map[decision]
        selection.reviewed_by = str(user["email"])
        selection.reviewed_at = datetime.now(UTC)
        selection.review_notes = normalized_notes
        selection.active = decision != "Rechazar"
        selection.applied_at = datetime.now(UTC) if decision == "Aprobar" else None
        selection.decision_snapshot = json.dumps({
            "compatibility_score": advice["score"],
            "breakdown": advice["breakdown"],
            "blockers": advice["blockers"],
            "hard_blockers": advice.get("hard_blockers", []),
            "review_decision": decision_map[decision],
            "reviewed_by": str(user["email"]),
            "reviewed_at": datetime.now(UTC).isoformat(),
        }, ensure_ascii=False)
        session.flush()
        recalculate_source(session, source)
        add_audit(
            session, int(user["organization_id"]), str(user["email"]), decision.upper(),
            "Factor por dato", f"Dato {record.id} · {selection.factor_version.factor.name}",
            detail=normalized_notes, new_value=selection.selection_status,
        )
        session.commit()
        message = "Factor aprobado y aplicado al cálculo." if decision == "Aprobar" else f"Selección marcada como {selection.selection_status.lower()}."
        set_flash(request, message)
        return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)


    @app.post("/fuentes/{source_id}/datos/{activity_data_id}/factores/{selection_id}/retirar")
    def remove_factor_from_record(
        source_id: int, activity_data_id: int, selection_id: int, request: Request,
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id).options(selectinload(EmissionSource.inventory)))
        record = session.get(ActivityData, activity_data_id)
        selection = session.scalar(select(ActivityFactorSelection).where(
            ActivityFactorSelection.id == selection_id, ActivityFactorSelection.activity_data_id == activity_data_id
        ).options(selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.factor)))
        if not source or source.inventory.organization_id != int(user["organization_id"]) or not record or record.source_id != source.id or not selection:
            raise HTTPException(404, "Selección no encontrada")
        selection.active = False
        selection.selection_status = "Retirado"
        selection.applied_at = None
        session.flush()
        recalculate_source(session, source)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RETIRAR", "Factor por dato", f"Dato {record.id} · {selection.factor_version.factor.name}")
        session.commit()
        set_flash(request, "La selección específica fue retirada; el dato vuelve a heredar los factores de la fuente cuando no queden selecciones aprobadas.")
        return RedirectResponse(f"/fuentes/{source.id}?activity_data_id={record.id}#conversacion-factor-{record.id}", status_code=303)


    @app.get("/api/fuentes/{source_id}/datos/{activity_data_id}/factores")
    def factor_conversation_api(
        source_id: int, activity_data_id: int,
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id).options(
            selectinload(EmissionSource.inventory),
            selectinload(EmissionSource.activity_records).selectinload(ActivityData.factor_selections).selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.factor),
            selectinload(EmissionSource.activity_records).selectinload(ActivityData.factor_selections).selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.gas),
        ))
        if not source or source.inventory.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Fuente no encontrada")
        record = next((item for item in source.activity_records if item.id == activity_data_id), None)
        if not record:
            raise HTTPException(404, "Dato no encontrado")
        versions = list(session.scalars(select(EmissionFactorVersion).where(EmissionFactorVersion.status == "Aprobado").options(
            selectinload(EmissionFactorVersion.factor), selectinload(EmissionFactorVersion.gas),
        )))
        conversation = conversation_for_record(session, source, record, versions)
        return {
            "record": {"id": record.id, "value": record.value, "unit": record.unit, "period_start": record.period_start.isoformat()},
            "selection_mode": conversation["selection_mode"],
            "control_status": conversation["control_status"],
            "warnings": conversation["warnings"],
            "selections": [
                {
                    "id": item.id,
                    "factor": item.factor_version.factor.name,
                    "factor_version_id": item.factor_version_id,
                    "status": item.selection_status,
                    "compatibility_score": item.compatibility_score,
                    "rationale": item.rationale,
                    "review_notes": item.review_notes,
                }
                for item in conversation["selections"]
            ],
            "candidates": [
                {
                    "factor_version_id": item["version"].id,
                    "factor": item["version"].factor.name,
                    "score": item["score"],
                    "recommendation": item["recommendation"],
                    "calculable": item["calculable"],
                    "breakdown": item["breakdown"],
                    "blockers": item["blockers"],
                }
                for item in conversation["candidates"]
            ],
        }


    @app.post("/fuentes/{source_id}/configurar")
    def source_configure(
        source_id: int,
        request: Request,
        name: str = Form(...),
        scope: int = Form(...),
        category: str = Form(...),
        facility_id: int | None = Form(None),
        responsible: str = Form(...),
        materiality: str = Form("Media"),
        data_frequency: str = Form("Mensual"),
        preferred_unit: str = Form(""),
        included: str | None = Form(None),
        exclusion_reason: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_sources")
        source = get_source_for_user(session, user, source_id)
        ensure_inventory_editable(source.inventory)
        facility = session.get(Facility, facility_id) if facility_id else None
        if facility and facility.organization_id != int(user["organization_id"]):
            raise HTTPException(400, "Sede inválida")
        included_facility_ids = {link.facility_id for link in source.inventory.facility_links if link.included}
        if facility and facility.id not in included_facility_ids:
            raise HTTPException(400, "La sede debe estar incluida en el inventario")
        normalized_name = name.strip()
        duplicate = session.scalar(
            select(EmissionSource).where(
                EmissionSource.inventory_id == source.inventory_id,
                EmissionSource.id != source.id,
                EmissionSource.name == normalized_name,
            )
        )
        if duplicate:
            raise HTTPException(400, "Ya existe una fuente con ese nombre")
        normalized_unit = preferred_unit.strip()
        if normalized_unit and normalized_unit not in ALLOWED_UNITS:
            raise HTTPException(400, "Unidad esperada no autorizada")
        will_be_included = included == "on"
        normalized_reason = exclusion_reason.strip()
        if not will_be_included and not normalized_reason:
            raise HTTPException(400, "Debes justificar la exclusión de la fuente")
        source.name = normalized_name
        source.scope = max(1, min(scope, 3))
        source.category = category.strip()
        source.facility_id = facility.id if facility else None
        source.responsible = responsible.strip() or "Responsable ambiental"
        source.materiality = materiality if materiality in {"Alta", "Media", "Baja"} else "Media"
        source.data_frequency = data_frequency if data_frequency in {"Mensual", "Trimestral", "Anual", "Por evento"} else "Mensual"
        source.preferred_unit = normalized_unit
        source.included = will_be_included
        source.exclusion_reason = "" if source.included else normalized_reason
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Fuente", source.name, f"Alcance {source.scope} · {source.category}")
        session.commit()
        set_flash(request, "La configuración de la fuente fue actualizada.")
        return RedirectResponse(f"/fuentes/{source.id}", status_code=303)


    @app.post("/fuentes/{source_id}/factores/asignar")
    def source_factor_assign(
        source_id: int,
        request: Request,
        factor_version_id: int = Form(...),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source = get_source_for_user(session, user, source_id)
        ensure_inventory_editable(source.inventory)
        factor_version = session.scalar(select(EmissionFactorVersion).where(EmissionFactorVersion.id == factor_version_id, EmissionFactorVersion.status == "Aprobado"))
        if not source or not factor_version:
            raise HTTPException(404, "Fuente o factor no encontrado")
        existing = session.scalar(select(SourceFactorAssignment).where(SourceFactorAssignment.source_id == source.id, SourceFactorAssignment.factor_version_id == factor_version.id))
        if existing:
            existing.active = True
            existing.notes = notes.strip()
            existing.assigned_by = str(user["email"])
        else:
            session.add(SourceFactorAssignment(source_id=source.id, factor_version_id=factor_version.id, active=True, assigned_by=str(user["email"]), notes=notes.strip()))
        session.flush()
        result = recalculate_source(session, source)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ASIGNAR", "Factor", source.name, f"Factor {factor_version.id} · {result['calculations']} cálculos")
        session.commit()
        set_flash(request, "El factor fue asignado y la fuente se recalculó.")
        return RedirectResponse(f"/fuentes/{source.id}", status_code=303)


    @app.post("/fuentes/{source_id}/factores/{assignment_id}/retirar")
    def source_factor_remove(
        source_id: int,
        assignment_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        assignment = session.scalar(
            select(SourceFactorAssignment)
            .join(EmissionSource)
            .join(Inventory)
            .where(SourceFactorAssignment.id == assignment_id, SourceFactorAssignment.source_id == source_id, Inventory.organization_id == int(user["organization_id"]))
            .options(selectinload(SourceFactorAssignment.source))
        )
        if not assignment:
            raise HTTPException(404, "Asignación no encontrada")
        ensure_inventory_editable(assignment.source.inventory)
        assignment.active = False
        session.flush()
        recalculate_source(session, assignment.source)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RETIRAR", "Factor", assignment.source.name, f"Asignación {assignment.id}")
        session.commit()
        set_flash(request, "El factor fue retirado y la fuente se recalculó.")
        return RedirectResponse(f"/fuentes/{source_id}", status_code=303)


    @app.post("/fuentes/{source_id}/recalcular")
    def source_recalculate(source_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        source = get_source_for_user(session, user, source_id)
        ensure_inventory_editable(source.inventory)
        result = recalculate_source(session, source)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RECALCULAR", "Fuente", source.name, f"{result['calculations']} componentes · {len(result['warnings'])} alertas")
        session.commit()
        level = "error" if result["warnings"] else "success"
        set_flash(request, f"Fuente recalculada: {result['emissions']:.3f} tCO₂e y {len(result['warnings'])} alertas.", level)
        return RedirectResponse(f"/fuentes/{source.id}", status_code=303)

