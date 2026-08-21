from __future__ import annotations

from datetime import date

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import CommercialLead, DiagnosticAssessment, ServicePlan, get_db
from .public_result_access import public_result_access_window_label, public_result_is_expired
from .repositories.organizations import get_organization
from .repositories.product_intelligence import (
    get_assessment,
    get_carbon_profile,
    latest_assessment,
    list_assessments,
    list_implementation_plans,
)
from .services.product_intelligence import (
    PACKAGE_DESCRIPTIONS,
    PACKAGE_LABELS,
    approve_assessment,
    assessment_view,
    build_implementation_plan,
    carbon_profile_view,
    create_assessment,
    plan_view,
    profile_payload,
    update_carbon_profile,
)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").replace("\n", ",").split(",") if item.strip()]


def _public_payload(
    *,
    company_name: str,
    sector: str,
    employees_band: str,
    facilities_count: int,
    countries_count: int,
    has_previous_inventory: bool,
    desired_scopes: str,
    objective: str,
    urgency: str,
    deadline_months: int,
    data_availability: str,
    evidence_readiness: str,
    reporting_frequency: str,
    assurance_ambition: str,
    has_fleet: bool,
    uses_fuels: bool,
    uses_refrigerants: bool,
    manages_waste: bool,
    has_wastewater: bool,
    has_agriculture: bool,
    relies_on_suppliers: bool,
    owns_generation: bool,
    has_process_emissions: bool,
    core_processes: str,
    current_data_systems: str,
) -> dict[str, object]:
    return {
        "company_name": company_name.strip(),
        "sector": sector.strip(),
        "employees_band": employees_band,
        "facilities_count": min(max(int(facilities_count), 1), 100),
        "countries_count": min(max(int(countries_count), 1), 50),
        "has_previous_inventory": has_previous_inventory,
        "desired_scopes": desired_scopes,
        "objective": objective,
        "urgency": urgency,
        "deadline_months": min(max(int(deadline_months), 1), 36),
        "data_availability": data_availability,
        "evidence_readiness": evidence_readiness,
        "reporting_frequency": reporting_frequency,
        "assurance_ambition": assurance_ambition,
        "has_fleet": has_fleet,
        "uses_fuels": uses_fuels,
        "uses_refrigerants": uses_refrigerants,
        "manages_waste": manages_waste,
        "has_wastewater": has_wastewater,
        "has_agriculture": has_agriculture,
        "relies_on_suppliers": relies_on_suppliers,
        "owns_generation": owns_generation,
        "has_process_emissions": has_process_emissions,
        "core_processes": _csv(core_processes),
        "current_data_systems": _csv(current_data_systems),
    }


def register_product_intelligence_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, settings
) -> None:
    @app.get("/diagnostico", response_class=HTMLResponse)
    def public_diagnostic(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="public_diagnosis.html",
            context={"app_settings": settings, "error": None},
        )

    @app.post("/diagnostico", response_class=HTMLResponse)
    def submit_public_diagnostic(
        request: Request,
        company_name: str = Form(...),
        contact_name: str = Form(...),
        email: str = Form(...),
        phone: str = Form(""),
        sector: str = Form(...),
        city: str = Form(""),
        employees_band: str = Form(...),
        facilities_count: int = Form(1),
        countries_count: int = Form(1),
        has_previous_inventory: str | None = Form(None),
        desired_scopes: str = Form(...),
        objective: str = Form(...),
        urgency: str = Form("Normal"),
        deadline_months: int = Form(12),
        data_availability: str = Form("Baja"),
        evidence_readiness: str = Form("Baja"),
        reporting_frequency: str = Form("Anual"),
        assurance_ambition: str = Form("Sin verificación externa"),
        has_fleet: str | None = Form(None),
        uses_fuels: str | None = Form(None),
        uses_refrigerants: str | None = Form(None),
        manages_waste: str | None = Form(None),
        has_wastewater: str | None = Form(None),
        has_agriculture: str | None = Form(None),
        relies_on_suppliers: str | None = Form(None),
        owns_generation: str | None = Form(None),
        has_process_emissions: str | None = Form(None),
        core_processes: str = Form(""),
        current_data_systems: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
    ):
        normalized_email = email.strip().lower()
        if "@" not in normalized_email or len(company_name.strip()) < 2 or len(contact_name.strip()) < 2:
            return templates.TemplateResponse(
                request=request,
                name="public_diagnosis.html",
                context={"app_settings": settings, "error": "Completa empresa, contacto y un correo válido."},
                status_code=400,
            )
        payload = _public_payload(
            company_name=company_name,
            sector=sector,
            employees_band=employees_band,
            facilities_count=facilities_count,
            countries_count=countries_count,
            has_previous_inventory=bool(has_previous_inventory),
            desired_scopes=desired_scopes,
            objective=objective,
            urgency=urgency if urgency in {"Normal", "Alta"} else "Normal",
            deadline_months=deadline_months,
            data_availability=data_availability,
            evidence_readiness=evidence_readiness,
            reporting_frequency=reporting_frequency,
            assurance_ambition=assurance_ambition,
            has_fleet=bool(has_fleet),
            uses_fuels=bool(uses_fuels),
            uses_refrigerants=bool(uses_refrigerants),
            manages_waste=bool(manages_waste),
            has_wastewater=bool(has_wastewater),
            has_agriculture=bool(has_agriculture),
            relies_on_suppliers=bool(relies_on_suppliers),
            owns_generation=bool(owns_generation),
            has_process_emissions=bool(has_process_emissions),
            core_processes=core_processes,
            current_data_systems=current_data_systems,
        )
        provisional = create_assessment(session, payload=payload, actor_email="diagnostico-publico-v045")
        lead = CommercialLead(
            public_token=__import__("secrets").token_urlsafe(24),
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            email=normalized_email,
            phone=phone.strip(),
            sector=sector.strip(),
            city=city.strip(),
            employees_band=employees_band,
            facilities_count=min(max(int(facilities_count), 1), 100),
            has_previous_inventory=bool(has_previous_inventory),
            desired_scopes=desired_scopes,
            objective=objective,
            urgency=urgency if urgency in {"Normal", "Alta"} else "Normal",
            notes=notes.strip(),
            complexity_score=provisional.total_score,
            recommended_plan_code=provisional.recommended_package_code,
            status="Nuevo",
            source="Diagnóstico inteligente V0.45",
        )
        session.add(lead)
        session.flush()
        provisional.lead_id = lead.id
        session.commit()
        return RedirectResponse(f"/diagnostico/gracias/{lead.public_token}", status_code=303)

    @app.get("/diagnostico/gracias/{token}", response_class=HTMLResponse)
    def diagnostic_thanks(token: str, request: Request, session: Session = Depends(get_db)):
        lead = session.scalar(select(CommercialLead).where(CommercialLead.public_token == token))
        if not lead or public_result_is_expired(
            lead.created_at,
            settings.public_result_max_age_hours,
        ):
            return templates.TemplateResponse(
                request=request,
                name="public_result_unavailable.html",
                context={"app_settings": settings},
                status_code=404,
            )
        plan = session.scalar(select(ServicePlan).where(ServicePlan.code == lead.recommended_plan_code))
        assessment = session.scalar(
            select(DiagnosticAssessment)
            .where(DiagnosticAssessment.lead_id == lead.id)
            .order_by(DiagnosticAssessment.id.desc())
            .limit(1)
        )
        return templates.TemplateResponse(
            request=request,
            name="public_thanks.html",
            context={
                "lead": lead,
                "plan": plan,
                "assessment": assessment_view(assessment),
                "package_labels": PACKAGE_LABELS,
                "public_result_access_window": public_result_access_window_label(
                    settings.public_result_max_age_hours
                ),
                "app_settings": settings,
            },
        )

    @app.get("/inteligencia-producto", response_class=HTMLResponse)
    def product_intelligence_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        capabilities = set(user["capabilities"])
        if not ({"manage_org", "view_methodology", "manage_portfolio", "view_consolidation"} & capabilities):
            raise HTTPException(403, "No tienes permisos para consultar el diagnóstico de producto.")
        organization = get_organization(session, int(user["organization_id"]), include_graph=True)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")
        profile = get_carbon_profile(session, organization.id)
        assessments = [assessment_view(item) for item in list_assessments(session, organization.id)]
        plans = [plan_view(item) for item in list_implementation_plans(session, organization.id)]
        current = assessments[0] if assessments else None
        return templates.TemplateResponse(
            request=request,
            name="product_intelligence.html",
            context=common_context(
                request,
                session,
                user,
                "product_intelligence",
                organization=organization,
                profile=carbon_profile_view(profile),
                assessments=assessments,
                latest_assessment=current,
                plans=plans,
                package_labels=PACKAGE_LABELS,
                package_descriptions=PACKAGE_DESCRIPTIONS,
            ),
        )

    @app.post("/inteligencia-producto/perfil")
    def save_product_profile(
        request: Request,
        company_size: str = Form("Por definir"),
        business_model: str = Form(""),
        sector_subsector: str = Form(""),
        operating_description: str = Form(""),
        countries_count: int = Form(1),
        countries: str = Form("Colombia"),
        facility_types: str = Form(""),
        core_processes: str = Form(""),
        energy_sources: str = Form(""),
        fleet_profile: str = Form(""),
        refrigerants_profile: str = Form(""),
        waste_profile: str = Form(""),
        wastewater_profile: str = Form(""),
        agriculture_land_use_profile: str = Form(""),
        key_materials: str = Form(""),
        supplier_profile: str = Form(""),
        reporting_drivers: str = Form(""),
        climate_goals: str = Form(""),
        current_data_systems: str = Form(""),
        inventory_history: str = Form("Sin inventario anterior"),
        data_availability: str = Form("Baja"),
        evidence_readiness: str = Form("Baja"),
        reporting_frequency: str = Form("Anual"),
        assurance_ambition: str = Form("Sin verificación externa"),
        inventory_owner: str = Form(""),
        executive_sponsor: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        organization = get_organization(session, int(user["organization_id"]), include_graph=True)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")
        profile = update_carbon_profile(
            session,
            organization,
            actor_email=str(user["email"]),
            payload={
                "company_size": company_size,
                "business_model": business_model,
                "sector_subsector": sector_subsector,
                "operating_description": operating_description,
                "countries_count": countries_count,
                "countries": _csv(countries),
                "facility_types": _csv(facility_types),
                "core_processes": _csv(core_processes),
                "energy_sources": _csv(energy_sources),
                "fleet_profile": fleet_profile,
                "refrigerants_profile": refrigerants_profile,
                "waste_profile": waste_profile,
                "wastewater_profile": wastewater_profile,
                "agriculture_land_use_profile": agriculture_land_use_profile,
                "key_materials": _csv(key_materials),
                "supplier_profile": supplier_profile,
                "reporting_drivers": _csv(reporting_drivers),
                "climate_goals": _csv(climate_goals),
                "current_data_systems": _csv(current_data_systems),
                "inventory_history": inventory_history,
                "data_availability": data_availability,
                "evidence_readiness": evidence_readiness,
                "reporting_frequency": reporting_frequency,
                "assurance_ambition": assurance_ambition,
                "inventory_owner": inventory_owner,
                "executive_sponsor": executive_sponsor,
            },
        )
        session.commit()
        set_flash(request, f"Perfil actualizado: {profile.profile_completion}% de completitud.")
        return RedirectResponse("/inteligencia-producto#perfil", status_code=303)

    @app.post("/inteligencia-producto/evaluar")
    def run_internal_assessment(
        request: Request,
        desired_scopes: str = Form("Alcances 1 y 2"),
        objective: str = Form("Conocer la huella corporativa"),
        urgency: str = Form("Normal"),
        deadline_months: int = Form(12),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        capabilities = set(user["capabilities"])
        if not ({"manage_org", "view_methodology", "manage_portfolio"} & capabilities):
            raise HTTPException(403, "No tienes permisos para ejecutar el diagnóstico.")
        organization = get_organization(session, int(user["organization_id"]), include_graph=True)
        if not organization:
            raise HTTPException(404, "Organización no encontrada")
        profile = get_carbon_profile(session, organization.id)
        if not profile:
            raise HTTPException(409, "Completa primero el perfil de la empresa.")
        payload = profile_payload(profile, organization)
        payload.update({
            "desired_scopes": desired_scopes,
            "objective": objective,
            "urgency": urgency,
            "deadline_months": deadline_months,
        })
        assessment = create_assessment(
            session,
            payload=payload,
            organization_id=organization.id,
            actor_email=str(user["email"]),
            is_demo=profile.source.startswith("Demo"),
        )
        session.commit()
        set_flash(
            request,
            f"Diagnóstico calculado: {assessment.complexity_level} · {PACKAGE_LABELS[assessment.recommended_package_code]}.",
        )
        return RedirectResponse("/inteligencia-producto#diagnostico", status_code=303)

    @app.post("/inteligencia-producto/evaluaciones/{assessment_id}/aprobar")
    def approve_internal_assessment(
        assessment_id: int,
        request: Request,
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"approve", "manage_org", "manage_portfolio"} & set(user["capabilities"])):
            raise HTTPException(403, "La aprobación requiere un rol autorizador.")
        assessment = get_assessment(session, int(user["organization_id"]), assessment_id)
        if not assessment:
            raise HTTPException(404, "Diagnóstico no encontrado")
        approve_assessment(session, assessment, actor_email=str(user["email"]), notes=notes)
        session.commit()
        set_flash(request, "Diagnóstico aprobado con trazabilidad.")
        return RedirectResponse("/inteligencia-producto#diagnostico", status_code=303)

    @app.post("/inteligencia-producto/evaluaciones/{assessment_id}/plan")
    def create_internal_plan(
        assessment_id: int,
        request: Request,
        owner: str = Form("Equipo del inventario"),
        start_date: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_org", "manage_portfolio", "manage_inventory", "view_methodology"} & set(user["capabilities"])):
            raise HTTPException(403, "No tienes permisos para crear el plan.")
        assessment = get_assessment(session, int(user["organization_id"]), assessment_id)
        if not assessment:
            raise HTTPException(404, "Diagnóstico no encontrado")
        parsed_start = date.fromisoformat(start_date) if start_date else date.today()
        plan = build_implementation_plan(
            session,
            assessment,
            actor_email=str(user["email"]),
            start_date=parsed_start,
            owner=owner,
        )
        session.commit()
        set_flash(request, f"Plan {plan.code} generado con {len(plan.items)} fases.")
        return RedirectResponse("/inteligencia-producto#plan", status_code=303)

    @app.get("/api/inteligencia-producto/resumen")
    def product_intelligence_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        organization = get_organization(session, int(user["organization_id"]), include_graph=True)
        profile = get_carbon_profile(session, int(user["organization_id"]))
        assessment = latest_assessment(session, int(user["organization_id"]))
        return {
            "version": settings.version,
            "organization": organization.trade_name or organization.name if organization else "",
            "profile_completion": profile.profile_completion if profile else 0,
            "profile_status": profile.status if profile else "Sin perfil",
            "assessment": assessment_view(assessment),
            "plan_count": len(list_implementation_plans(session, int(user["organization_id"]))),
        }