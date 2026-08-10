from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import secrets
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .database import (
    ActivityData,
    ActivityIndicator,
    AppUser,
    AuditEvent,
    DataRequest,
    EmissionCalculation,
    EmissionFactor,
    EmissionFactorVersion,
    EmissionSource,
    EmissionTarget,
    ReductionScenario,
    ReductionScenarioAction,
    VerificationFinding,
    EvidenceDocument,
    Facility,
    Gas,
    GWPValue,
    Inventory,
    InventoryFacility,
    InventoryDecision,
    Notification,
    NotificationPreference,
    OrganizationMembership,
    ScheduledAutomation,
    AutomationRun,
    PlatformSetting,
    MethodologyRelease,
    InventoryMethodologySnapshot,
    ComplianceRequirement,
    ComplianceAssessment,
    DocumentControlRecord,
    CommercialReadinessItem,
    ServicePlan,
    OrganizationSubscription,
    UsageCounter,
    CustomerOnboardingItem,
    SupportTicket,
    SupportMessage,
    BillingInvoice,
    CommercialLead,
    CommercialProposal,
    PaymentTransaction,
    ServiceContract,
    ServiceOrder,
    CollectionAction,
    BillingDocumentRecord,
    CustomerSuccessProfile,
    AccountHealthSnapshot,
    ValueMilestone,
    SuccessCommitment,
    RenewalOpportunity,
    BenchmarkReference,
    ImpactSnapshot,
    ClimateRiskAssessment,
    ClimateRisk,
    ClimateRiskControl,
    ClimateTransitionRoadmap,
    ClimateTransitionAction,
    ClimateScenarioDefinition,
    ClimateDisclosureStatement,
    ClimateDisclosureRequirement,
    ClimateBoardBriefing,
    ClimateBoardDecision,
    ConsolidationFinding,
    ReleaseGate,
    JourneyValidation,
    Organization,
    ReviewObservation,
    ReductionAction,
    ReportArtifact,
    SectorTemplate,
    SectorTemplateSource,
    SourceFactorAssignment,
    Supplier,
    SupplierCampaign,
    Scope3CategoryAssessment,
    SupplierDataRequest,
    SupplierResponse,
    UnitConversion,
    UnitDefinition,
    INSTANCE_DIR,
    UPLOAD_DIR,
    SessionLocal,
    add_audit,
    get_db,
    refresh_progress,
    hash_password,
)
from .config import settings
from .accounting import is_gross_source
from .inventory_context import (
    ensure_inventory_editable,
    get_inventory,
    get_source_for_user,
    inventory_metrics,
)
from .inventory_lifecycle import clone_inventory_version, next_inventory_version
from .sectorization_web import register_sectorization_routes
from .calculation_web import register_calculation_routes
from .methodology_admin_web import register_methodology_admin_routes
from .supply_chain_web import register_supply_chain_routes
from .support_web import register_support_routes
from .commercial_web import register_commercial_routes
from .payment_web import register_payment_routes
from .commercial_operations_web import register_commercial_operations_routes
from .customer_success_web import register_customer_success_routes
from .access_control import ROLE_CAPABILITIES, can_open_route
from .product_registry import PRODUCT_MODULES
from .product_experience import demo_story_for, journey_detail, navigation_for, normalize_view_mode, role_profile
from .onboarding_experience import onboarding_summary
from .guided_onboarding import load_profile as load_guided_profile, decision_plan as guided_decision_plan
from .consolidation import consolidation_summary, build_consolidation_workbook, summary_json
from .architecture import domain_architecture_summary
from .methodology_web import register_methodology_core_routes
from .factor_library_web import register_factor_library_routes
from .methodology_closure_web import register_methodology_closure_routes
from .land_removals_web import register_land_removals_routes
from .product_project_assurance_web import register_product_project_assurance_routes
from .colombia_library_web import register_colombia_library_routes
from .pilot_web import register_pilot_routes
from .pilot_execution_web import register_pilot_execution_routes
from .data_quality_web import register_data_quality_routes
from .period_close_web import register_period_close_routes
from .operational_imports_web import register_operational_import_routes
from .operations_web import register_operations_routes
from .integrations_web import register_integration_routes
from .users_web import register_user_routes
from .inventories_web import register_inventory_routes
from .reports_web import register_report_routes
from .reduction_web import register_reduction_routes
from .delivery_web import register_delivery_routes
from .delivery_readiness import professional_delivery_summary
from .organizations_web import register_organization_routes
from .information_web import register_information_routes
from .capture_web import register_capture_routes
from .review_web import register_review_routes
from .demo_web import register_demo_routes
from .product_intelligence_web import register_product_intelligence_routes
from .guided_onboarding_web import register_guided_onboarding_routes
from .service_operations_web import register_service_operations_routes
from .experience_web import register_experience_routes
from .workflow_web import register_workflow_routes
from .legal_web import register_legal_routes
from .public_web import register_public_routes
from .auth_web import register_auth_routes
from .user_context import resolve_current_user
from .period_close import assert_periods_editable
from .pilot_execution import guided_workspace
from .storage import storage, StorageError
from .notifications import create_notification, notify_roles, get_or_create_preference, process_pending_notifications
from .automations import AUTOMATION_TYPES, CADENCES, ROLE_OPTIONS, calculate_next_run, execute_automation, process_due_automations
from .security import (CSRFMiddleware, RequestBodyLimitMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware, login_throttle, password_needs_upgrade, validate_upload_bytes, verify_password)
from .operations import diagnostic_snapshot
from .observability import OperationalMetricsMiddleware
from .calculations import convert_value, normalize_factor_output, recalculate_inventory, recalculate_source, source_calculation_summary
from .analytics import full_analysis, indicator_metrics, reduction_summary
from .reporting import create_report_artifact
from .scenarios import get_scenario, portfolio_macc, scenario_summary
from .reduction_portfolio import build_portfolio_workbook, portfolio_json, portfolio_summary
from .verification import create_verification_package
from .customer_success import account_metrics, refresh_account_health, sync_renewal_opportunity
from .support_workflow import (
    OPEN_STATUSES, CLOSED_STATUSES, add_support_message, ensure_reference, response_deadline,
    route_assignment, status_class, support_summary, ticket_context, ticket_overdue, ticket_waiting_days,
)
from .impact_intelligence import impact_metrics, refresh_impact_snapshot, compare_benchmarks, portfolio_comparison
from .climate_risk import assessment_summary, calculate_risk_scores, risk_level, synchronize_control_effectiveness, refresh_assessment_status
from .climate_disclosure import scenario_comparison, disclosure_summary, board_summary, build_board_pdf
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
from .scope3_catalog import canonical_category_label, category_from_value

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=settings.app_name, version=settings.version, docs_url=None if settings.is_production else "/docs", redoc_url=None)
app.add_middleware(OperationalMetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=settings.session_https_only,
)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def format_number(value: float, decimals: int = 1) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

templates.env.filters["number_es"] = format_number

def parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, "Fecha inválida") from exc

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_SIZE = settings.max_upload_mb * 1024 * 1024
ALLOWED_UNITS = ["kWh", "MWh", "L", "gal", "m³", "kg", "t", "km", "t·km", "pasajero·km", "COP", "unidad", "servicio anual", "tCO₂e"]
DATA_ORIGINS = ["Medición directa", "Factura", "Registro operativo", "Registro contable", "Información de proveedor", "Certificado", "Encuesta", "Estimación"]

def safe_filename(name: str) -> str:
    base = Path(name).name.strip().replace(" ", "_")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base[:140] or "archivo"

def quality_from(origin: str, is_estimated: bool, has_evidence: bool) -> str:
    if origin == "Medición directa" and has_evidence and not is_estimated:
        return "A"
    if origin in {"Factura", "Registro operativo", "Registro contable", "Información de proveedor", "Certificado"} and not is_estimated:
        return "B"
    if origin in {"Encuesta", "Estimación"} or is_estimated:
        return "C"
    return "D"

def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"

templates.env.filters["bytes"] = format_bytes

def current_user(request: Request) -> dict[str, object] | None:
    return resolve_current_user(request)

def require_user(request: Request) -> dict[str, object]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    return user

def ensure_capability(user: dict[str, object], capability: str) -> None:
    if capability not in user["capabilities"]:
        raise HTTPException(403, "Tu rol no tiene permiso para esta acción")

def set_flash(request: Request, message: str, level: str = "success") -> None:
    request.session["flash"] = {"message": message, "level": level}

def common_context(request: Request, session: Session, user: dict[str, object], active: str, **extra):
    org = session.get(Organization, int(user["organization_id"]))
    flash = request.session.pop("flash", None)
    unread_notifications = session.scalar(select(func.count(Notification.id)).where(
        Notification.organization_id == int(user["organization_id"]),
        Notification.user_id == int(user["id"]),
        Notification.read_at.is_(None),
    )) or 0
    view_mode = normalize_view_mode(user.get("view_mode"))
    return {
        "user": user,
        "org": org,
        "active": active,
        "flash": flash,
        "unread_notifications": unread_notifications,
        "navigation": navigation_for(user, view_mode),
        "role_profile": role_profile(str(user.get("role", "Cliente"))),
        "can_open_route": can_open_route,
        **extra,
    }

def review_gate_summary(session: Session, inventory: Inventory) -> dict[str, object]:
    included_sources = [source for source in inventory.sources if source.included]
    incomplete = [source for source in included_sources if source.progress < 100]
    missing_factors = [source for source in included_sources if source.category != "Datos específicos de proveedores" and not any(item.active and item.factor_version.status == "Aprobado" for item in source.factor_assignments)]
    error_count = session.scalar(
        select(func.count()).select_from(EmissionCalculation).join(ActivityData).join(EmissionSource).where(
            EmissionSource.inventory_id == inventory.id, EmissionCalculation.status == "Error"
        )
    ) or 0
    open_observations = [item for item in inventory.observations if item.status != "Cerrada"]
    blocking_observations = [item for item in open_observations if item.severity in {"Mayor", "Crítica"}]
    config_ok = bool(inventory.methodology and inventory.gwp_version and inventory.facility_links)
    sources_ok = not incomplete
    factors_ok = not missing_factors and error_count == 0
    review_ok = not blocking_observations
    gates = [
        {"name": "Configuración metodológica", "status": "Aprobado" if config_ok else "Pendiente", "detail": "Metodología, GWP, periodo y límites definidos." if config_ok else "Completa metodología, GWP y sedes incluidas."},
        {"name": "Cobertura de fuentes", "status": "Aprobado" if sources_ok else "En progreso", "detail": "Todas las fuentes incluidas tienen cobertura completa." if sources_ok else f"{len(incomplete)} fuente(s) todavía no tienen cobertura completa."},
        {"name": "Factores y cálculos", "status": "Aprobado" if factors_ok else "En progreso", "detail": "Todas las fuentes tienen factores aprobados y cálculos sin error." if factors_ok else f"{len(missing_factors)} fuente(s) sin factor y {error_count} error(es) de cálculo."},
        {"name": "Revisión profesional", "status": "Aprobado" if review_ok else "En progreso", "detail": "No existen observaciones mayores o críticas abiertas." if review_ok else f"{len(blocking_observations)} observación(es) bloqueante(s) abierta(s)."},
    ]
    blockers = []
    if not config_ok:
        blockers.append("Configuración metodológica incompleta")
    if incomplete:
        blockers.append(f"{len(incomplete)} fuentes incompletas")
    if missing_factors:
        blockers.append(f"{len(missing_factors)} fuentes sin factor aprobado")
    if error_count:
        blockers.append(f"{error_count} errores de cálculo")
    if blocking_observations:
        blockers.append(f"{len(blocking_observations)} observaciones mayores o críticas")
    return {
        "gates": gates,
        "blockers": blockers,
        "can_approve": not blockers,
        "open_observations": open_observations,
        "blocking_observations": blocking_observations,
        "incomplete_sources": incomplete,
        "error_count": error_count,
    }

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": str(exc.detail)}, status_code=401)
    return RedirectResponse("/login", status_code=303)

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with SessionLocal() as session:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context=common_context(request, session, user, "", title="Acceso restringido", message=str(exc.detail)),
            status_code=403,
        )

@app.post("/preferencias/vista")
def update_view_mode(
    request: Request,
    mode: str = Form(...),
    return_url: str = Form("/dashboard"),
    user: dict = Depends(require_user),
):
    request.session["view_mode"] = normalize_view_mode(mode)
    destination = return_url if return_url.startswith("/") and not return_url.startswith("//") else "/dashboard"
    set_flash(
        request,
        "Vista esencial activada: se prioriza el flujo del inventario."
        if request.session["view_mode"] == "essential"
        else "Vista completa activada: se muestran capacidades avanzadas e internas.",
    )
    return RedirectResponse(destination, status_code=303)

@app.get("/recorrido-inventario", response_class=HTMLResponse)
def inventory_journey_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    inventory = get_inventory(session, user)
    workspace = guided_workspace(session, user, inventory)
    journey = journey_detail(workspace, str(user["role"]))
    session.commit()
    return templates.TemplateResponse(
        request=request,
        name="inventory_journey.html",
        context=common_context(
            request,
            session,
            user,
            "journey",
            inventory=inventory,
            journey=journey,
        ),
    )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    inventory = get_inventory(session, user)
    metrics = inventory_metrics(inventory)
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
    tasks = list(session.scalars(
        select(DataRequest)
        .where(
            DataRequest.inventory_id == inventory.id,
            DataRequest.status.notin_(["Completada", "Cerrada"]),
        )
        .order_by(DataRequest.due_date)
    ))
    workspace = guided_workspace(session, user, inventory)
    delivery = professional_delivery_summary(session, inventory)
    dashboard_action = delivery["next_action"]
    if str(user["role"]) == "Cliente":
        if tasks:
            dashboard_action = {
                "name": "Atender solicitudes de información",
                "detail": f"Tienes {len(tasks)} requerimiento(s) activo(s). Completa los datos o soportes solicitados antes de la revisión técnica.",
                "owner": "Responsable de información",
                "acceptance": "Solicitudes respondidas y evidencias vinculadas al periodo correcto.",
                "href": "/informacion#solicitudes",
                "action": "Abrir pendientes",
            }
        else:
            dashboard_action = {
                "name": "Completar datos y evidencias",
                "detail": "Revisa los periodos pendientes y conserva un soporte verificable para cada valor relevante.",
                "owner": "Responsable de información",
                "acceptance": "Fuentes del periodo completas y soportes vinculados.",
                "href": "/captura-guiada",
                "action": "Continuar captura",
            }
    onboarding_rows = list(session.scalars(select(CustomerOnboardingItem).where(
        CustomerOnboardingItem.organization_id == int(user["organization_id"])
    ).order_by(CustomerOnboardingItem.display_order)))
    onboarding_state = onboarding_summary(onboarding_rows, inventory_id=inventory.id)
    guided_profile = load_guided_profile(session, inventory.organization)
    guided_setup = guided_decision_plan(guided_profile, inventory.organization, inventory=inventory)
    session.commit()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=common_context(
            request, session, user, "dashboard", inventory=inventory, inventories=inventories,
            tasks=tasks, sources=inventory.sources, workspace=workspace, delivery=delivery,
            dashboard_action=dashboard_action,
            journey=journey_detail(workspace, str(user["role"])), onboarding=onboarding_state,
            guided_setup=guided_setup, demo_story=demo_story_for(inventory.organization.trade_name), **metrics,
        ),
    )

def _parse_excel_period(value: object, inventory: Inventory) -> tuple[date, date]:
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        for pattern in ("%Y-%m", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(text, pattern).date()
                break
            except ValueError:
                parsed = None
        if parsed is None:
            raise ValueError("periodo inválido")
    start = date(parsed.year, parsed.month, 1)
    if parsed.month == 12:
        next_month = date(parsed.year + 1, 1, 1)
    else:
        next_month = date(parsed.year, parsed.month + 1, 1)
    end = date.fromordinal(next_month.toordinal() - 1)
    if start < inventory.start_date or end > inventory.end_date:
        raise ValueError("periodo fuera del inventario")
    return start, end

@app.get("/analisis", response_class=HTMLResponse)
def analysis_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    inventory = get_inventory(session, user)
    analysis = full_analysis(session, inventory)
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context=common_context(
            request, session, user, "analysis", inventory=inventory,
            indicator_types=[("Producción", "t"), ("Empleados", "personas"), ("Ingresos", "COP"), ("Servicios", "servicios"), ("Área", "m²")],
            **analysis,
        ),
    )

@app.post("/analisis/indicadores/nuevo")
def create_indicator(
    request: Request,
    inventory_id: int = Form(...),
    indicator_type: str = Form(...),
    value: float = Form(...),
    unit: str = Form(...),
    period_start: str = Form(...),
    period_end: str = Form(...),
    source_name: str = Form("Registro operativo"),
    facility_id: int | None = Form(None),
    notes: str = Form(""),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_inventory")
    inventory = get_inventory(session, user, inventory_id)
    ensure_inventory_editable(inventory)
    if value < 0:
        raise HTTPException(400, "El valor del indicador no puede ser negativo")
    indicator = ActivityIndicator(
        inventory_id=inventory.id, facility_id=facility_id or None,
        period_start=parse_date(period_start), period_end=parse_date(period_end),
        indicator_type=indicator_type.strip(), value=value, unit=unit.strip(),
        source_name=source_name.strip() or "Registro operativo", notes=notes.strip(),
        status="Cargado", created_by=str(user["email"]),
    )
    session.add(indicator)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Indicador", indicator.indicator_type, f"{value} {unit}")
    session.commit()
    set_flash(request, "Indicador operativo registrado.")
    return RedirectResponse("/analisis", status_code=303)

@app.post("/analisis/indicadores/{indicator_id}/editar")
def update_indicator(
    indicator_id: int, request: Request, value: float = Form(...), unit: str = Form(...),
    source_name: str = Form("Registro operativo"), notes: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_inventory")
    indicator = session.scalar(
        select(ActivityIndicator).join(Inventory).where(
            ActivityIndicator.id == indicator_id, Inventory.organization_id == int(user["organization_id"])
        )
    )
    if not indicator:
        raise HTTPException(404, "Indicador no encontrado")
    inventory = get_inventory(session, user, indicator.inventory_id)
    ensure_inventory_editable(inventory)
    previous = f"{indicator.value} {indicator.unit}"
    indicator.value = value
    indicator.unit = unit.strip()
    indicator.source_name = source_name.strip() or indicator.source_name
    indicator.notes = notes.strip()
    add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Indicador", indicator.indicator_type, previous_value=previous, new_value=f"{value} {unit}")
    session.commit()
    set_flash(request, "Indicador actualizado.")
    return RedirectResponse("/analisis", status_code=303)

@app.get("/escenarios", response_class=HTMLResponse)
def scenarios_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    inventory = get_inventory(session, user)
    scenarios = list(session.scalars(
        select(ReductionScenario)
        .where(ReductionScenario.inventory_id == inventory.id)
        .options(selectinload(ReductionScenario.action_links).selectinload(ReductionScenarioAction.action))
        .order_by(ReductionScenario.created_at.desc())
    ))
    selected_id = request.query_params.get("scenario_id")
    selected = None
    if selected_id and selected_id.isdigit():
        selected = get_scenario(session, int(selected_id), int(user["organization_id"]))
    if not selected and scenarios:
        selected = get_scenario(session, scenarios[0].id, int(user["organization_id"]))
    selected_summary = scenario_summary(selected) if selected else None
    macc = portfolio_macc(inventory.reduction_actions, selected.discount_rate if selected else 10.0)
    return templates.TemplateResponse(
        request=request,
        name="scenarios.html",
        context=common_context(
            request, session, user, "scenarios", inventory=inventory, scenarios=scenarios,
            selected=selected, selected_summary=selected_summary, actions=inventory.reduction_actions,
            portfolio_macc=macc,
        ),
    )

@app.post("/escenarios/nuevo")
def create_scenario(
    request: Request, inventory_id: int = Form(...), name: str = Form(...), description: str = Form(""),
    start_year: int = Form(...), target_year: int = Form(...), discount_rate: float = Form(10.0),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_inventory")
    inventory = get_inventory(session, user, inventory_id)
    ensure_inventory_editable(inventory)
    if target_year < start_year:
        raise HTTPException(400, "El año objetivo no puede ser anterior al año inicial")
    scenario = ReductionScenario(
        inventory_id=inventory.id, name=name.strip(), description=description.strip(), start_year=start_year,
        target_year=target_year, discount_rate=max(0.0, discount_rate), status="Borrador", created_by=str(user["email"]),
    )
    session.add(scenario)
    session.flush()
    for action in inventory.reduction_actions:
        session.add(ReductionScenarioAction(
            scenario_id=scenario.id, action_id=action.id, included=False,
            implementation_year=action.implementation_year or start_year, adoption_percent=100.0,
        ))
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Escenario", scenario.name, f"Periodo {start_year}-{target_year}")
    session.commit()
    set_flash(request, "Escenario creado. Selecciona las medidas que harán parte del portafolio.")
    return RedirectResponse(f"/escenarios?scenario_id={scenario.id}", status_code=303)

@app.post("/escenarios/{scenario_id}/configurar")
async def configure_scenario(
    scenario_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_inventory")
    scenario = get_scenario(session, scenario_id, int(user["organization_id"]))
    if not scenario:
        raise HTTPException(404, "Escenario no encontrado")
    ensure_inventory_editable(scenario.inventory)
    form = await request.form()
    scenario.status = str(form.get("status") or scenario.status)
    discount_rate = float(form.get("discount_rate") or scenario.discount_rate)
    scenario.discount_rate = max(0.0, discount_rate)
    for link in scenario.action_links:
        link.included = f"include_{link.action_id}" in form
        try:
            link.adoption_percent = min(100.0, max(0.0, float(form.get(f"adoption_{link.action_id}") or 100)))
        except (TypeError, ValueError):
            link.adoption_percent = 100.0
        try:
            link.implementation_year = int(form.get(f"year_{link.action_id}") or scenario.start_year)
        except (TypeError, ValueError):
            link.implementation_year = scenario.start_year
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CONFIGURAR", "Escenario", scenario.name, "Portafolio, adopción y cronograma actualizados")
    session.commit()
    set_flash(request, "Escenario recalculado correctamente.")
    return RedirectResponse(f"/escenarios?scenario_id={scenario.id}", status_code=303)

@app.get("/verificacion", response_class=HTMLResponse)
def verification_portal(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    if not (user["can_external_audit"] or user["can_review"] or user["can_approve"]):
        raise HTTPException(403, "Tu rol no tiene acceso al portal de verificación")
    inventory = get_inventory(session, user)
    gate = review_gate_summary(session, inventory)
    findings = list(session.scalars(
        select(VerificationFinding)
        .where(VerificationFinding.inventory_id == inventory.id)
        .options(selectinload(VerificationFinding.source))
        .order_by(VerificationFinding.status == "Cerrado", VerificationFinding.created_at.desc())
    ))
    reports = list(session.scalars(select(ReportArtifact).where(ReportArtifact.inventory_id == inventory.id).order_by(ReportArtifact.generated_at.desc())))
    decisions = list(session.scalars(select(InventoryDecision).where(InventoryDecision.inventory_id == inventory.id).order_by(InventoryDecision.decided_at.desc())))
    calculations_count = session.scalar(
        select(func.count()).select_from(EmissionCalculation).join(ActivityData).join(EmissionSource).where(EmissionSource.inventory_id == inventory.id)
    ) or 0
    evidence_with_files = sum(1 for item in inventory.documents if item.stored_name and storage.exists(item.stored_name))
    finding_counts = {
        "open": sum(1 for item in findings if item.status != "Cerrado"),
        "major": sum(1 for item in findings if item.status != "Cerrado" and item.severity in {"Mayor", "Crítica"}),
        "closed": sum(1 for item in findings if item.status == "Cerrado"),
    }
    return templates.TemplateResponse(
        request=request,
        name="verification.html",
        context=common_context(
            request, session, user, "verification", inventory=inventory, findings=findings, reports=reports,
            decisions=decisions, calculations_count=calculations_count, evidence_with_files=evidence_with_files,
            finding_counts=finding_counts, **gate,
        ),
    )

@app.post("/verificacion/hallazgos/nuevo")
def create_verification_finding(
    request: Request, inventory_id: int = Form(...), title: str = Form(...), description: str = Form(...),
    finding_type: str = Form("Observación"), severity: str = Form("Menor"), source_id: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "external_audit")
    inventory = get_inventory(session, user, inventory_id)
    selected_source_id = int(source_id) if source_id.isdigit() else None
    if selected_source_id and not any(item.id == selected_source_id for item in inventory.sources):
        raise HTTPException(400, "La fuente no pertenece al inventario")
    finding = VerificationFinding(
        inventory_id=inventory.id, source_id=selected_source_id, title=title.strip(), description=description.strip(),
        finding_type=finding_type, severity=severity, status="Abierto", verifier_email=str(user["email"]),
    )
    session.add(finding)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Hallazgo de verificación", finding.title, f"{finding_type} · {severity}")
    session.commit()
    set_flash(request, "Hallazgo registrado en el expediente de verificación.")
    return RedirectResponse("/verificacion", status_code=303)

@app.post("/verificacion/hallazgos/{finding_id}/responder")
def respond_verification_finding(
    finding_id: int, request: Request, management_response: str = Form(...),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    if not (user["can_manage_inventory"] or user["can_provide_data"] or user["can_review"]):
        raise HTTPException(403, "Tu rol no puede responder hallazgos")
    finding = session.scalar(
        select(VerificationFinding).join(Inventory).where(
            VerificationFinding.id == finding_id, Inventory.organization_id == int(user["organization_id"])
        )
    )
    if not finding:
        raise HTTPException(404, "Hallazgo no encontrado")
    finding.management_response = management_response.strip()
    finding.response_by = str(user["email"])
    finding.response_at = datetime.now(UTC)
    finding.status = "Respondido"
    add_audit(session, int(user["organization_id"]), str(user["email"]), "RESPONDER", "Hallazgo de verificación", finding.title, management_response[:180])
    session.commit()
    set_flash(request, "Respuesta enviada al verificador.")
    return RedirectResponse("/verificacion", status_code=303)

@app.post("/verificacion/hallazgos/{finding_id}/cerrar")
def close_verification_finding(
    finding_id: int, request: Request, conclusion: str = Form(...), decision: str = Form("Cerrar"),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "external_audit")
    finding = session.scalar(
        select(VerificationFinding).join(Inventory).where(
            VerificationFinding.id == finding_id, Inventory.organization_id == int(user["organization_id"])
        )
    )
    if not finding:
        raise HTTPException(404, "Hallazgo no encontrado")
    finding.conclusion = conclusion.strip()
    finding.closed_by = str(user["email"])
    if decision == "Cerrar":
        finding.status = "Cerrado"
        finding.closed_at = datetime.now(UTC)
    else:
        finding.status = "Abierto"
        finding.closed_at = None
    add_audit(session, int(user["organization_id"]), str(user["email"]), decision.upper(), "Hallazgo de verificación", finding.title, conclusion[:180])
    session.commit()
    set_flash(request, "Decisión del verificador registrada.")
    return RedirectResponse("/verificacion", status_code=303)

@app.post("/verificacion/paquete")
def generate_verification_package(
    request: Request, inventory_id: int = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    if not (user["can_external_audit"] or user["can_review"] or user["can_approve"]):
        raise HTTPException(403, "Tu rol no puede generar el paquete de verificación")
    inventory = get_inventory(session, user, inventory_id)
    artifact = create_verification_package(session, inventory, str(user["email"]))
    add_audit(session, int(user["organization_id"]), str(user["email"]), "GENERAR", "Paquete de verificación", artifact.file_name, artifact.sha256)
    session.commit()
    set_flash(request, "Paquete de verificación generado con manifiesto, índices y archivos disponibles.")
    return RedirectResponse("/verificacion", status_code=303)

@app.get("/notificaciones", response_class=HTMLResponse)
def notifications_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    notifications = list(session.scalars(select(Notification).where(
        Notification.organization_id == int(user["organization_id"]),
        Notification.user_id == int(user["id"]),
    ).order_by(Notification.created_at.desc()).limit(100)))
    preference = get_or_create_preference(session, int(user["id"]))
    session.commit()
    return templates.TemplateResponse(
        request=request,
        name="notifications.html",
        context=common_context(request, session, user, "notifications", notifications=notifications, preference=preference),
    )

@app.post("/notificaciones/{notification_id}/leer")
def notification_read(notification_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    notification = session.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.organization_id == int(user["organization_id"]),
        Notification.user_id == int(user["id"]),
    ))
    if not notification:
        raise HTTPException(404, "Notificación no encontrada")
    notification.read_at = datetime.now(UTC)
    session.commit()
    return RedirectResponse(notification.link or "/notificaciones", status_code=303)

@app.post("/notificaciones/leer-todas")
def notifications_read_all(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    notifications = list(session.scalars(select(Notification).where(
        Notification.organization_id == int(user["organization_id"]),
        Notification.user_id == int(user["id"]),
        Notification.read_at.is_(None),
    )))
    now = datetime.now(UTC)
    for notification in notifications:
        notification.read_at = now
    session.commit()
    set_flash(request, "Todas las notificaciones quedaron marcadas como leídas.")
    return RedirectResponse("/notificaciones", status_code=303)

@app.post("/notificaciones/preferencias")
def notification_preferences_update(
    request: Request,
    email_enabled: str | None = Form(None),
    in_app_enabled: str | None = Form(None),
    digest_frequency: str = Form("Inmediato"),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    preference = get_or_create_preference(session, int(user["id"]))
    preference.email_enabled = email_enabled == "on"
    preference.in_app_enabled = in_app_enabled == "on"
    preference.digest_frequency = digest_frequency if digest_frequency in {"Inmediato", "Diario", "Semanal"} else "Inmediato"
    session.commit()
    set_flash(request, "Preferencias de notificación actualizadas.")
    return RedirectResponse("/notificaciones", status_code=303)

@app.get("/administracion-plataforma", response_class=HTMLResponse)
def platform_admin_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_operations")
    users = list(session.scalars(
        select(AppUser).join(OrganizationMembership).where(
            OrganizationMembership.organization_id == int(user["organization_id"]),
            OrganizationMembership.active.is_(True),
        ).order_by(AppUser.name)
    ))
    settings_rows = list(session.scalars(select(PlatformSetting).where(PlatformSetting.organization_id == int(user["organization_id"])).order_by(PlatformSetting.key)))
    notification_stats = {
        "total": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]))) or 0,
        "pending": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]), Notification.status.in_(["Pendiente", "Error"]))) or 0,
        "unread": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == int(user["organization_id"]), Notification.read_at.is_(None))) or 0,
    }
    storage_status = storage.diagnostics()
    return templates.TemplateResponse(
        request=request,
        name="platform_admin.html",
        context=common_context(request, session, user, "platform_admin", users=users, settings_rows=settings_rows, notification_stats=notification_stats, storage_status=storage_status, app_settings=settings),
    )

@app.post("/administracion-plataforma/configuracion")
def platform_setting_update(
    request: Request,
    key: str = Form(...),
    value: str = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_operations")
    clean_key = re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_")
    if not clean_key:
        raise HTTPException(400, "Clave inválida")
    row = session.scalar(select(PlatformSetting).where(PlatformSetting.organization_id == int(user["organization_id"]), PlatformSetting.key == clean_key))
    if not row:
        row = PlatformSetting(organization_id=int(user["organization_id"]), key=clean_key)
        session.add(row)
    row.value = value.strip()
    row.description = description.strip()
    row.updated_by = str(user["email"])
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CONFIGURAR", "Plataforma", clean_key, value.strip())
    session.commit()
    set_flash(request, "Configuración guardada.")
    return RedirectResponse("/administracion-plataforma", status_code=303)

@app.post("/administracion-plataforma/notificaciones/prueba")
def platform_test_notification(
    request: Request,
    role: str = Form("Administrador"),
    title: str = Form("Prueba de notificación"),
    message: str = Form("El centro de notificaciones está operativo."),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_operations")
    created = notify_roles(session, int(user["organization_id"]), {role}, title, message, link="/notificaciones", category="Prueba", email_requested=True)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "NOTIFICAR", "Plataforma", role, f"{len(created)} destinatarios")
    session.commit()
    set_flash(request, f"Se generaron {len(created)} notificaciones de prueba.")
    return RedirectResponse("/administracion-plataforma", status_code=303)

@app.post("/administracion-plataforma/notificaciones/procesar")
def platform_process_notifications(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_operations")
    result = process_pending_notifications(session, settings.notification_batch_size)
    session.commit()
    set_flash(request, f"Cola procesada: {result['sent']} enviadas y {result['failed']} con error.")
    return RedirectResponse("/administracion-plataforma", status_code=303)

@app.get("/portafolio", response_class=HTMLResponse)
def portfolio_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_portfolio")
    memberships = list(session.scalars(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == int(user["id"]), OrganizationMembership.active.is_(True))
        .options(selectinload(OrganizationMembership.organization).selectinload(Organization.inventories))
        .order_by(OrganizationMembership.id)
    ))
    portfolio = []
    for membership in memberships:
        org_item = membership.organization
        inventories = org_item.inventories if org_item else []
        portfolio.append({
            "membership": membership,
            "organization": org_item,
            "inventories": inventories,
            "latest_inventory": sorted(inventories, key=lambda item: (item.start_date, item.id), reverse=True)[0] if inventories else None,
            "demo_story": demo_story_for(org_item.trade_name) if org_item else None,
        })
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context=common_context(request, session, user, "portfolio", portfolio=portfolio),
    )

@app.post("/portafolio/cambiar/{organization_id}")
def portfolio_switch(organization_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    membership = session.scalar(select(OrganizationMembership).where(
        OrganizationMembership.user_id == int(user["id"]),
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
    ))
    if not membership:
        raise HTTPException(403, "No tienes acceso a esta organización")
    request.session["active_org_id"] = organization_id
    add_audit(session, organization_id, str(user["email"]), "CAMBIAR", "Organización activa", str(organization_id), "Cambio de contexto multiempresa")
    session.commit()
    set_flash(request, "Organización activa actualizada.")
    return RedirectResponse("/dashboard", status_code=303)

@app.post("/portafolio/nueva")
def portfolio_create(
    request: Request,
    name: str = Form(...),
    trade_name: str = Form(""),
    tax_id: str = Form(...),
    sector: str = Form(...),
    city: str = Form("Medellín"),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_org")
    if session.scalar(select(Organization).where(func.lower(Organization.name) == name.strip().lower())):
        raise HTTPException(409, "Ya existe una organización con ese nombre")
    organization = Organization(
        name=name.strip(), trade_name=trade_name.strip() or name.strip(), tax_id=tax_id.strip(),
        sector=sector.strip(), country="Colombia", department="Antioquia", city=city.strip(),
        contact_name=str(user["name"]), contact_email=str(user["email"]), status="Activa",
    )
    session.add(organization)
    session.flush()
    session.add(OrganizationMembership(
        user_id=int(user["id"]), organization_id=organization.id, role="Administrador", active=True,
    ))
    add_audit(session, organization.id, str(user["email"]), "CREAR", "Organización", organization.name, "Alta desde portafolio multiempresa")
    session.commit()
    request.session["active_org_id"] = organization.id
    set_flash(request, "Organización creada. Ahora puedes configurar sedes e inventarios.")
    return RedirectResponse("/organizacion", status_code=303)

@app.get("/automatizaciones", response_class=HTMLResponse)
def automations_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_automations")
    automations = list(session.scalars(
        select(ScheduledAutomation)
        .where(ScheduledAutomation.organization_id == int(user["organization_id"]))
        .options(selectinload(ScheduledAutomation.inventory), selectinload(ScheduledAutomation.runs))
        .order_by(ScheduledAutomation.active.desc(), ScheduledAutomation.name)
    ))
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
    recent_runs = list(session.scalars(
        select(AutomationRun)
        .join(ScheduledAutomation)
        .where(ScheduledAutomation.organization_id == int(user["organization_id"]))
        .options(selectinload(AutomationRun.automation))
        .order_by(AutomationRun.started_at.desc()).limit(30)
    ))
    return templates.TemplateResponse(
        request=request,
        name="automations.html",
        context=common_context(
            request, session, user, "automations", automations=automations, inventories=inventories,
            recent_runs=recent_runs, automation_types=AUTOMATION_TYPES, cadences=CADENCES,
            role_options=ROLE_OPTIONS, scheduler_enabled=settings.scheduler_enabled,
        ),
    )

@app.post("/automatizaciones/nueva")
def automation_create(
    request: Request,
    name: str = Form(...),
    automation_type: str = Form(...),
    cadence: str = Form("Semanal"),
    schedule_time: str = Form("08:00"),
    inventory_id: int | None = Form(None),
    weekday: int | None = Form(None),
    month_day: int | None = Form(None),
    days_before: int = Form(3),
    recipient_roles: list[str] = Form(default=[]),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_automations")
    if automation_type not in AUTOMATION_TYPES or cadence not in CADENCES:
        raise HTTPException(400, "Tipo o frecuencia inválida")
    if inventory_id:
        get_inventory(session, user, inventory_id)
    automation = ScheduledAutomation(
        organization_id=int(user["organization_id"]), inventory_id=inventory_id or None,
        name=name.strip(), automation_type=automation_type, cadence=cadence,
        schedule_time=schedule_time, weekday=weekday, month_day=month_day,
        timezone="America/Bogota", recipient_roles=json.dumps(recipient_roles or ["Administrador", "Consultor"]),
        days_before=max(0, min(days_before, 60)), active=True, created_by=str(user["email"]),
    )
    session.add(automation)
    session.flush()
    automation.next_run_at = calculate_next_run(automation)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Automatización", automation.name, automation.automation_type)
    session.commit()
    set_flash(request, "Automatización creada y programada.")
    return RedirectResponse("/automatizaciones", status_code=303)

@app.post("/automatizaciones/{automation_id}/estado")
def automation_toggle(automation_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_automations")
    automation = session.scalar(select(ScheduledAutomation).where(
        ScheduledAutomation.id == automation_id,
        ScheduledAutomation.organization_id == int(user["organization_id"]),
    ))
    if not automation:
        raise HTTPException(404, "Automatización no encontrada")
    automation.active = not automation.active
    automation.next_run_at = calculate_next_run(automation) if automation.active else None
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTIVAR" if automation.active else "DESACTIVAR", "Automatización", automation.name)
    session.commit()
    set_flash(request, f"Automatización {'activada' if automation.active else 'desactivada'}.")
    return RedirectResponse("/automatizaciones", status_code=303)

@app.post("/automatizaciones/{automation_id}/ejecutar")
def automation_run_now(automation_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_automations")
    automation = session.scalar(select(ScheduledAutomation).where(
        ScheduledAutomation.id == automation_id,
        ScheduledAutomation.organization_id == int(user["organization_id"]),
    ))
    if not automation:
        raise HTTPException(404, "Automatización no encontrada")
    run = execute_automation(session, automation, triggered_by=str(user["email"]))
    add_audit(session, int(user["organization_id"]), str(user["email"]), "EJECUTAR", "Automatización", automation.name, run.summary)
    session.commit()
    set_flash(request, f"Ejecución {run.status.lower()}: {run.summary}", "success" if run.status == "Ejecutado" else "warning")
    return RedirectResponse("/automatizaciones", status_code=303)

@app.post("/automatizaciones/procesar-vencidas")
def automations_process_due(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_automations")
    result = process_due_automations(session)
    set_flash(request, f"Programación revisada: {result['executed']} ejecuciones y {result['errors']} errores.")
    return RedirectResponse("/automatizaciones", status_code=303)

def _compliance_score(rows: list[ComplianceAssessment]) -> int:
    applicable = [row for row in rows if row.status != "No aplica"]
    if not applicable:
        return 0
    weights = {"Cumple": 100, "Parcial": 50, "Pendiente": 0, "No cumple": 0}
    return round(sum(weights.get(row.status, 0) for row in applicable) / len(applicable))

@app.get("/direccion-ejecutiva", response_class=HTMLResponse)
def executive_portfolio_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_portfolio")
    memberships = list(session.scalars(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == int(user["id"]), OrganizationMembership.active.is_(True))
        .options(selectinload(OrganizationMembership.organization))
        .order_by(OrganizationMembership.id)
    ))
    cards = []
    portfolio_total = 0.0
    total_reduction = 0.0
    for membership in memberships:
        organization = membership.organization
        inventory = session.scalar(select(Inventory).where(Inventory.organization_id == organization.id).order_by(Inventory.start_date.desc(), Inventory.id.desc()).limit(1))
        if inventory:
            emissions = session.scalar(select(func.coalesce(func.sum(EmissionSource.emissions), 0.0)).where(EmissionSource.inventory_id == inventory.id, EmissionSource.included.is_(True))) or 0.0
            assessments = list(session.scalars(select(ComplianceAssessment).where(ComplianceAssessment.inventory_id == inventory.id).options(selectinload(ComplianceAssessment.requirement))))
            open_observations = session.scalar(select(func.count(ReviewObservation.id)).where(ReviewObservation.inventory_id == inventory.id, ReviewObservation.status != "Cerrada")) or 0
            reduction = session.scalar(select(func.coalesce(func.sum(ReductionAction.expected_reduction), 0.0)).where(ReductionAction.inventory_id == inventory.id)) or 0.0
            documents = session.scalar(select(func.count(DocumentControlRecord.id)).where(DocumentControlRecord.organization_id == organization.id)) or 0
            portfolio_total += float(emissions)
            total_reduction += float(reduction)
            cards.append({"organization": organization, "membership": membership, "inventory": inventory, "emissions": float(emissions), "compliance": _compliance_score(assessments), "open_observations": open_observations, "reduction": float(reduction), "documents": documents})
        else:
            cards.append({"organization": organization, "membership": membership, "inventory": None, "emissions": 0.0, "compliance": 0, "open_observations": 0, "reduction": 0.0, "documents": 0})
    average_compliance = round(sum(item["compliance"] for item in cards) / max(len(cards), 1))
    return templates.TemplateResponse(request=request, name="executive_portfolio.html", context=common_context(request, session, user, "executive", cards=cards, portfolio_total=portfolio_total, total_reduction=total_reduction, average_compliance=average_compliance))

@app.get("/cumplimiento", response_class=HTMLResponse)
def compliance_page(request: Request, inventory_id: int | None = None, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "view_compliance")
    inventory = get_inventory(session, user, inventory_id)
    rows = list(session.scalars(
        select(ComplianceAssessment)
        .where(ComplianceAssessment.inventory_id == inventory.id)
        .options(selectinload(ComplianceAssessment.requirement), selectinload(ComplianceAssessment.evidence))
        .join(ComplianceRequirement)
        .order_by(ComplianceRequirement.display_order)
    ))
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
    score = _compliance_score(rows)
    by_framework = {}
    for row in rows:
        by_framework.setdefault(row.requirement.framework, []).append(row)
    return templates.TemplateResponse(request=request, name="compliance.html", context=common_context(request, session, user, "compliance", inventory=inventory, inventories=inventories, rows=rows, by_framework=by_framework, compliance_score=score, documents=inventory.documents))

@app.post("/cumplimiento/{assessment_id}/actualizar")
def compliance_update(assessment_id: int, request: Request, status: str = Form(...), owner: str = Form("Responsable ambiental"), evidence_id: int | None = Form(None), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_compliance")
    assessment = session.scalar(select(ComplianceAssessment).join(Inventory).where(ComplianceAssessment.id == assessment_id, Inventory.organization_id == int(user["organization_id"])).options(selectinload(ComplianceAssessment.requirement)))
    if not assessment:
        raise HTTPException(404, "Evaluación no encontrada")
    if status not in {"Cumple", "Parcial", "Pendiente", "No cumple", "No aplica"}:
        raise HTTPException(400, "Estado inválido")
    if evidence_id:
        evidence = session.scalar(select(EvidenceDocument).where(EvidenceDocument.id == evidence_id, EvidenceDocument.inventory_id == assessment.inventory_id))
        if not evidence:
            raise HTTPException(400, "La evidencia no pertenece al inventario")
    assessment.status = status
    assessment.owner = owner.strip()
    assessment.evidence_id = evidence_id or None
    assessment.notes = notes.strip()
    assessment.updated_by = str(user["email"])
    add_audit(session, int(user["organization_id"]), str(user["email"]), "EVALUAR", "Cumplimiento", assessment.requirement.code, f"Estado {status}")
    session.commit()
    set_flash(request, "Evaluación de cumplimiento actualizada.")
    return RedirectResponse(f"/cumplimiento?inventory_id={assessment.inventory_id}", status_code=303)

@app.get("/gobierno-metodologico", response_class=HTMLResponse)
def methodology_governance_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_methodology_governance")
    releases = list(session.scalars(select(MethodologyRelease).where(MethodologyRelease.organization_id == int(user["organization_id"])).order_by(MethodologyRelease.created_at.desc())))
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
    snapshots = list(session.scalars(select(InventoryMethodologySnapshot).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).options(selectinload(InventoryMethodologySnapshot.inventory), selectinload(InventoryMethodologySnapshot.release)).order_by(InventoryMethodologySnapshot.created_at.desc())))
    return templates.TemplateResponse(request=request, name="methodology_governance.html", context=common_context(request, session, user, "methodology_governance", releases=releases, inventories=inventories, snapshots=snapshots))

@app.post("/gobierno-metodologico/versiones/nueva")
def methodology_release_create(request: Request, name: str = Form(...), version: str = Form(...), issuing_body: str = Form("Calcula tu Huella"), publication_date: str = Form(""), effective_from: str = Form(""), source_reference: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_methodology_governance")
    if session.scalar(select(MethodologyRelease).where(MethodologyRelease.organization_id == int(user["organization_id"]), MethodologyRelease.name == name.strip(), MethodologyRelease.version == version.strip())):
        raise HTTPException(409, "La versión metodológica ya existe")
    fingerprint = hashlib.sha256(f"{name}|{version}|{source_reference}|{notes}".encode()).hexdigest()
    release = MethodologyRelease(organization_id=int(user["organization_id"]), name=name.strip(), version=version.strip(), issuing_body=issuing_body.strip(), publication_date=parse_date(publication_date) if publication_date else None, effective_from=parse_date(effective_from) if effective_from else None, status="Borrador", source_reference=source_reference.strip(), content_hash=fingerprint, notes=notes.strip())
    session.add(release)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Versión metodológica", f"{release.name} {release.version}", fingerprint)
    session.commit()
    set_flash(request, "Versión metodológica creada en borrador.")
    return RedirectResponse("/gobierno-metodologico", status_code=303)

@app.post("/gobierno-metodologico/versiones/{release_id}/aprobar")
def methodology_release_approve(release_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_methodology_governance")
    release = session.scalar(select(MethodologyRelease).where(MethodologyRelease.id == release_id, MethodologyRelease.organization_id == int(user["organization_id"])))
    if not release:
        raise HTTPException(404, "Versión no encontrada")
    release.status = "Aprobado"
    release.approved_by = str(user["email"])
    release.approved_at = datetime.now(UTC)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "APROBAR", "Versión metodológica", f"{release.name} {release.version}")
    session.commit()
    set_flash(request, "Versión metodológica aprobada.")
    return RedirectResponse("/gobierno-metodologico", status_code=303)

@app.post("/gobierno-metodologico/snapshots/nuevo")
def methodology_snapshot_create(request: Request, inventory_id: int = Form(...), methodology_release_id: int | None = Form(None), snapshot_name: str = Form(...), policy_notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_methodology_governance")
    inventory = get_inventory(session, user, inventory_id)
    release = None
    if methodology_release_id:
        release = session.scalar(select(MethodologyRelease).where(MethodologyRelease.id == methodology_release_id, MethodologyRelease.organization_id == int(user["organization_id"])))
        if not release:
            raise HTTPException(400, "Versión metodológica inválida")
    snapshot = InventoryMethodologySnapshot(inventory_id=inventory.id, methodology_release_id=release.id if release else None, snapshot_name=snapshot_name.strip(), status="Aprobado", methodology_name=inventory.methodology, methodology_version=inventory.methodology_version, gwp_version=inventory.gwp_version, consolidation_approach=inventory.consolidation_approach, materiality_threshold=inventory.materiality_threshold, policy_json=json.dumps({"notes": policy_notes.strip(), "inventory_version": inventory.version}, ensure_ascii=False), approved_by=str(user["email"]), approved_at=datetime.now(UTC))
    session.add(snapshot)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CONGELAR", "Snapshot metodológico", snapshot.snapshot_name, f"Inventario #{inventory.id}")
    session.commit()
    set_flash(request, "Configuración metodológica congelada para el inventario.")
    return RedirectResponse("/gobierno-metodologico", status_code=303)

@app.get("/centro-documental", response_class=HTMLResponse)
def document_center_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_documents")
    records = list(session.scalars(select(DocumentControlRecord).where(DocumentControlRecord.organization_id == int(user["organization_id"])).options(selectinload(DocumentControlRecord.inventory), selectinload(DocumentControlRecord.evidence), selectinload(DocumentControlRecord.report)).order_by(DocumentControlRecord.category, DocumentControlRecord.document_code)))
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
    evidence = list(session.scalars(select(EvidenceDocument).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(EvidenceDocument.uploaded_at.desc()).limit(100)))
    reports = list(session.scalars(select(ReportArtifact).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(ReportArtifact.generated_at.desc()).limit(100)))
    due = [row for row in records if row.review_due and row.review_due <= date.today()]
    return templates.TemplateResponse(request=request, name="document_center.html", context=common_context(request, session, user, "documents", records=records, inventories=inventories, evidence=evidence, reports=reports, due=due))

@app.post("/centro-documental/registros/nuevo")
def document_record_create(request: Request, document_code: str = Form(...), title: str = Form(...), category: str = Form("Soporte"), version: str = Form("1.0"), owner: str = Form("Gestión ambiental"), confidentiality: str = Form("Interno"), retention_years: int = Form(7), review_due: str = Form(""), inventory_id: int | None = Form(None), evidence_document_id: int | None = Form(None), report_artifact_id: int | None = Form(None), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_documents")
    organization_id = int(user["organization_id"])
    if session.scalar(select(DocumentControlRecord).where(DocumentControlRecord.organization_id == organization_id, DocumentControlRecord.document_code == document_code.strip())):
        raise HTTPException(409, "El código documental ya existe")
    inventory = get_inventory(session, user, inventory_id) if inventory_id else None
    evidence = None
    report = None
    if evidence_document_id:
        evidence = session.scalar(select(EvidenceDocument).join(Inventory).where(EvidenceDocument.id == evidence_document_id, Inventory.organization_id == organization_id))
        if not evidence:
            raise HTTPException(400, "Evidencia inválida")
    if report_artifact_id:
        report = session.scalar(select(ReportArtifact).join(Inventory).where(ReportArtifact.id == report_artifact_id, Inventory.organization_id == organization_id))
        if not report:
            raise HTTPException(400, "Informe inválido")
    row = DocumentControlRecord(organization_id=organization_id, inventory_id=inventory.id if inventory else None, evidence_document_id=evidence.id if evidence else None, report_artifact_id=report.id if report else None, document_code=document_code.strip(), title=title.strip(), category=category.strip(), version=version.strip(), owner=owner.strip(), confidentiality=confidentiality, retention_years=max(1, retention_years), review_due=parse_date(review_due) if review_due else None, status="Vigente", sha256=(evidence.sha256 if evidence else (report.sha256 if report else "")), notes=notes.strip(), created_by=str(user["email"]))
    session.add(row)
    add_audit(session, organization_id, str(user["email"]), "REGISTRAR", "Documento controlado", row.document_code, row.title)
    session.commit()
    set_flash(request, "Documento incorporado al registro maestro.")
    return RedirectResponse("/centro-documental", status_code=303)

@app.post("/centro-documental/registros/{record_id}/actualizar")
def document_record_update(record_id: int, request: Request, status: str = Form(...), version: str = Form(...), owner: str = Form(...), confidentiality: str = Form(...), review_due: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_documents")
    row = session.scalar(select(DocumentControlRecord).where(DocumentControlRecord.id == record_id, DocumentControlRecord.organization_id == int(user["organization_id"])))
    if not row:
        raise HTTPException(404, "Documento no encontrado")
    row.status = status
    row.version = version.strip()
    row.owner = owner.strip()
    row.confidentiality = confidentiality
    row.review_due = parse_date(review_due) if review_due else None
    row.notes = notes.strip()
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Documento controlado", row.document_code, f"Versión {row.version} · {row.status}")
    session.commit()
    set_flash(request, "Control documental actualizado.")
    return RedirectResponse("/centro-documental", status_code=303)

@app.get("/alistamiento", response_class=HTMLResponse)
def readiness_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_readiness")
    rows = list(session.scalars(select(CommercialReadinessItem).where(CommercialReadinessItem.organization_id == int(user["organization_id"])).order_by(CommercialReadinessItem.display_order)))
    weights = {"Completado": 100, "En progreso": 50, "Pendiente": 0, "Bloqueado": 0}
    score = round(sum(weights.get(row.status, 0) for row in rows) / max(len(rows), 1))
    categories = {}
    for row in rows:
        categories.setdefault(row.category, []).append(row)
    return templates.TemplateResponse(request=request, name="readiness.html", context=common_context(request, session, user, "readiness", rows=rows, categories=categories, readiness_score=score))

@app.post("/alistamiento/{item_id}/actualizar")
def readiness_update(item_id: int, request: Request, status: str = Form(...), owner: str = Form(...), due_date: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_readiness")
    row = session.scalar(select(CommercialReadinessItem).where(CommercialReadinessItem.id == item_id, CommercialReadinessItem.organization_id == int(user["organization_id"])))
    if not row:
        raise HTTPException(404, "Elemento no encontrado")
    if status not in {"Completado", "En progreso", "Pendiente", "Bloqueado"}:
        raise HTTPException(400, "Estado inválido")
    row.status = status
    row.owner = owner.strip()
    row.due_date = parse_date(due_date) if due_date else None
    row.notes = notes.strip()
    row.updated_by = str(user["email"])
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Alistamiento comercial", row.title, status)
    session.commit()
    set_flash(request, "Elemento de alistamiento actualizado.")
    return RedirectResponse("/alistamiento", status_code=303)

def _service_usage(session: Session, organization_id: int, plan: ServicePlan | None) -> dict[str, object]:
    users = session.scalar(select(func.count(OrganizationMembership.id)).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.active.is_(True),
    )) or 0
    facilities = session.scalar(select(func.count(Facility.id)).where(Facility.organization_id == organization_id)) or 0
    inventories = session.scalar(select(func.count(Inventory.id)).where(Inventory.organization_id == organization_id)) or 0
    storage_bytes = session.scalar(
        select(func.coalesce(func.sum(EvidenceDocument.file_size), 0))
        .join(Inventory, EvidenceDocument.inventory_id == Inventory.id)
        .where(Inventory.organization_id == organization_id)
    ) or 0
    storage_mb = round(float(storage_bytes) / (1024 * 1024), 2)
    values = {
        "users": {"value": int(users), "limit": plan.max_users if plan else 0, "label": "Usuarios"},
        "facilities": {"value": int(facilities), "limit": plan.max_facilities if plan else 0, "label": "Sedes"},
        "inventories": {"value": int(inventories), "limit": plan.max_inventories if plan else 0, "label": "Inventarios"},
        "storage": {"value": storage_mb, "limit": plan.max_storage_mb if plan else 0, "label": "Almacenamiento MB"},
    }
    period = date.today().replace(day=1)
    metric_map = {"users": users, "facilities": facilities, "inventories": inventories, "storage_mb": storage_mb}
    for metric, value in metric_map.items():
        counter = session.scalar(select(UsageCounter).where(
            UsageCounter.organization_id == organization_id,
            UsageCounter.metric == metric,
            UsageCounter.period_start == period,
        ))
        if counter:
            counter.value = float(value)
        else:
            session.add(UsageCounter(organization_id=organization_id, metric=metric, period_start=period, value=float(value)))
    for item in values.values():
        limit = float(item["limit"] or 0)
        item["percentage"] = min(100, round(float(item["value"]) / limit * 100)) if limit else 0
        item["exceeded"] = bool(limit and float(item["value"]) > limit)
    return values

@app.get("/cuenta-servicio", response_class=HTMLResponse)
def service_account(request: Request, session: Session = Depends(get_db)):
    user = require_user(request)
    subscription = session.scalar(
        select(OrganizationSubscription)
        .where(OrganizationSubscription.organization_id == int(user["organization_id"]))
        .options(selectinload(OrganizationSubscription.plan))
    )
    plans = list(session.scalars(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.monthly_fee)))
    usage = _service_usage(session, int(user["organization_id"]), subscription.plan if subscription else None)
    invoices = list(session.scalars(select(BillingInvoice).where(BillingInvoice.organization_id == int(user["organization_id"])).order_by(BillingInvoice.issued_at.desc())))
    session.commit()
    return templates.TemplateResponse(request, "service_account.html", common_context(
        request, session, user, "service_account", subscription=subscription, plans=plans, usage=usage, invoices=invoices,
    ))

@app.post("/cuenta-servicio/suscripcion")
def update_subscription(
    request: Request,
    plan_id: int = Form(...),
    billing_cycle: str = Form("Anual"),
    session: Session = Depends(get_db),
):
    user = require_user(request)
    ensure_capability(user, "manage_subscription")
    plan = session.get(ServicePlan, plan_id)
    if not plan or not plan.active:
        raise HTTPException(404, "Plan no disponible")
    subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == int(user["organization_id"])))
    previous = subscription.plan_id if subscription else None
    if subscription:
        subscription.plan_id = plan.id
        subscription.billing_cycle = billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual"
        subscription.status = "Activa"
        subscription.start_date = date.today()
    else:
        subscription = OrganizationSubscription(
            organization_id=int(user["organization_id"]), plan_id=plan.id,
            billing_cycle=billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual",
            status="Activa", start_date=date.today(),
        )
        session.add(subscription)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Suscripción", plan.name, previous_value=str(previous or ""), new_value=str(plan.id))
    session.commit()
    set_flash(request, f"Plan actualizado a {plan.name}. Esta operación es administrativa y no procesa pagos.")
    return RedirectResponse("/cuenta-servicio", status_code=303)

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding(request: Request, session: Session = Depends(get_db)):
    user = require_user(request)
    inventory = get_inventory(session, user)
    rows = list(session.scalars(select(CustomerOnboardingItem).where(
        CustomerOnboardingItem.organization_id == int(user["organization_id"])
    ).order_by(CustomerOnboardingItem.display_order)))
    onboarding_state = onboarding_summary(rows, inventory_id=inventory.id)
    return templates.TemplateResponse(request, "onboarding.html", common_context(
        request, session, user, "onboarding", inventory=inventory, rows=rows,
        onboarding=onboarding_state, onboarding_score=onboarding_state["score"],
    ))

@app.post("/onboarding/{item_id}/actualizar")
def update_onboarding_item(
    item_id: int,
    request: Request,
    status: str = Form(...),
    owner: str = Form(""),
    due_date: str = Form(""),
    session: Session = Depends(get_db),
):
    user = require_user(request)
    if not (user["can_manage_org"] or user["can_manage_inventory"]):
        raise HTTPException(403, "Tu rol no puede modificar el onboarding")
    row = session.scalar(select(CustomerOnboardingItem).where(
        CustomerOnboardingItem.id == item_id,
        CustomerOnboardingItem.organization_id == int(user["organization_id"]),
    ))
    if not row:
        raise HTTPException(404, "Actividad de onboarding no encontrada")
    row.status = status if status in {"Pendiente", "En progreso", "Completado", "Bloqueado"} else "Pendiente"
    row.owner = owner.strip() or row.owner
    row.due_date = parse_date(due_date) if due_date else None
    row.completed_at = datetime.now(UTC) if row.status == "Completado" else None
    row.updated_by = str(user["email"])
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Onboarding", row.title, new_value=row.status)
    session.commit()
    set_flash(request, "Actividad de onboarding actualizada.")
    return RedirectResponse("/onboarding", status_code=303)

@app.get("/administracion-saas", response_class=HTMLResponse)
def saas_admin(request: Request, session: Session = Depends(get_db)):
    user = require_user(request)
    ensure_capability(user, "manage_saas")
    plans = list(session.scalars(select(ServicePlan).order_by(ServicePlan.monthly_fee)))
    subscriptions = list(session.scalars(
        select(OrganizationSubscription)
        .options(selectinload(OrganizationSubscription.organization), selectinload(OrganizationSubscription.plan))
        .order_by(OrganizationSubscription.id)
    ))
    invoices = list(session.scalars(select(BillingInvoice).order_by(BillingInvoice.issued_at.desc()).limit(50)))
    organizations = list(session.scalars(select(Organization).order_by(Organization.name)))
    summary = {
        "active": sum(1 for item in subscriptions if item.status == "Activa"),
        "trial": sum(1 for item in subscriptions if item.status == "Prueba"),
        "mrr": round(sum((item.custom_monthly_fee or (item.plan.monthly_fee if item.plan else 0)) for item in subscriptions if item.status in {"Activa", "Prueba"})),
        "organizations": len(organizations),
    }
    return templates.TemplateResponse(request, "saas_admin.html", common_context(
        request, session, user, "saas_admin", plans=plans, subscriptions=subscriptions,
        invoices=invoices, organizations=organizations, summary=summary,
    ))

@app.post("/administracion-saas/planes/nuevo")
def create_service_plan(
    request: Request,
    code: str = Form(...), name: str = Form(...), description: str = Form(""),
    monthly_fee: float = Form(0), annual_fee: float = Form(0),
    max_users: int = Form(5), max_facilities: int = Form(3), max_inventories: int = Form(3), max_storage_mb: int = Form(1024),
    includes_scope3: str | None = Form(None), includes_verification_portal: str | None = Form(None),
    session: Session = Depends(get_db),
):
    user = require_user(request)
    ensure_capability(user, "manage_saas")
    normalized_code = re.sub(r"[^A-Z0-9_-]", "", code.upper())
    if not normalized_code or session.scalar(select(ServicePlan).where(ServicePlan.code == normalized_code)):
        raise HTTPException(400, "Código de plan inválido o duplicado")
    plan = ServicePlan(
        code=normalized_code, name=name.strip(), description=description.strip(), monthly_fee=max(0, monthly_fee), annual_fee=max(0, annual_fee),
        max_users=max(1, max_users), max_facilities=max(1, max_facilities), max_inventories=max(1, max_inventories), max_storage_mb=max(100, max_storage_mb),
        includes_scope3=bool(includes_scope3), includes_verification_portal=bool(includes_verification_portal), active=True,
    )
    session.add(plan)
    add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Plan SaaS", plan.name, detail=plan.code)
    session.commit()
    set_flash(request, f"Plan {plan.name} creado.")
    return RedirectResponse("/administracion-saas", status_code=303)

@app.post("/administracion-saas/suscripciones/{subscription_id}/actualizar")
def admin_update_subscription(
    subscription_id: int,
    request: Request,
    plan_id: int = Form(...), status: str = Form(...), billing_cycle: str = Form("Anual"),
    custom_monthly_fee: str = Form(""), renewal_date: str = Form(""), notes: str = Form(""),
    session: Session = Depends(get_db),
):
    user = require_user(request)
    ensure_capability(user, "manage_saas")
    subscription = session.get(OrganizationSubscription, subscription_id)
    plan = session.get(ServicePlan, plan_id)
    if not subscription or not plan:
        raise HTTPException(404, "Suscripción o plan no encontrado")
    subscription.plan_id = plan.id
    subscription.status = status if status in {"Prueba", "Activa", "Suspendida", "Cancelada"} else subscription.status
    subscription.billing_cycle = billing_cycle if billing_cycle in {"Mensual", "Anual"} else subscription.billing_cycle
    subscription.custom_monthly_fee = float(custom_monthly_fee) if custom_monthly_fee.strip() else None
    subscription.renewal_date = parse_date(renewal_date) if renewal_date else None
    subscription.notes = notes.strip()
    session.commit()
    set_flash(request, f"Suscripción de {subscription.organization.name} actualizada.")
    return RedirectResponse("/administracion-saas", status_code=303)

@app.post("/administracion-saas/facturas/{invoice_id}/estado")
def update_invoice_status(
    invoice_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db),
):
    user = require_user(request)
    ensure_capability(user, "manage_saas")
    invoice = session.get(BillingInvoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Registro de cobro no encontrado")
    invoice.status = status if status in {"Pendiente", "Pagada", "Vencida", "Anulada", "Demostrativa"} else invoice.status
    invoice.paid_at = datetime.now(UTC) if invoice.status == "Pagada" else None
    session.commit()
    set_flash(request, f"Estado de {invoice.reference} actualizado.")
    return RedirectResponse("/administracion-saas", status_code=303)

def _lead_complexity(employees_band: str, facilities_count: int, desired_scopes: str, has_previous_inventory: bool, objective: str, urgency: str) -> tuple[int, str]:
    employee_points = {"1 a 20": 1, "21 a 50": 2, "51 a 200": 4, "Más de 200": 6}.get(employees_band, 2)
    score = employee_points + min(max(facilities_count, 1), 8)
    if "3" in desired_scopes:
        score += 3
    if has_previous_inventory:
        score += 1
    if any(keyword in objective.lower() for keyword in ("verificación", "regulator", "licitación")):
        score += 2
    if urgency == "Alta":
        score += 1
    plan = "ESENCIAL" if score <= 5 else "EMPRESARIAL" if score <= 12 else "CORPORATIVO"
    return score, plan

def _require_impact_view(user: dict[str, object]) -> None:
    capabilities = user.get("capabilities", set())
    if "view_impact" not in capabilities and "manage_impact" not in capabilities:
        raise HTTPException(403, "Tu rol no tiene acceso a inteligencia de impacto")

@app.get("/inteligencia-impacto", response_class=HTMLResponse)
def impact_intelligence_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_impact_view(user)
    organization_id = int(user["organization_id"])
    metrics = impact_metrics(session, organization_id)
    snapshot = session.scalar(
        select(ImpactSnapshot).where(ImpactSnapshot.organization_id == organization_id).order_by(ImpactSnapshot.calculated_at.desc())
    )
    if not snapshot:
        snapshot = refresh_impact_snapshot(session, organization_id, created_by=str(user["email"]))
        session.commit()
    references = list(session.scalars(
        select(BenchmarkReference).where(BenchmarkReference.organization_id == organization_id, BenchmarkReference.status == "Activo").order_by(BenchmarkReference.metric_name)
    ))
    comparisons = compare_benchmarks(metrics, references)
    history = list(session.scalars(
        select(ImpactSnapshot).where(ImpactSnapshot.organization_id == organization_id).order_by(ImpactSnapshot.calculated_at.desc()).limit(12)
    ))
    organization_ids = [int(item["id"]) for item in user.get("organizations", [])]
    portfolio = portfolio_comparison(session, organization_ids or [organization_id], organization_id)
    return templates.TemplateResponse(
        request=request, name="impact_intelligence.html",
        context=common_context(request, session, user, "impact", metrics=metrics, snapshot=snapshot, references=references, comparisons=comparisons, history=history, portfolio=portfolio),
    )

@app.post("/inteligencia-impacto/recalcular")
def recalculate_impact(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_impact")
    snapshot = refresh_impact_snapshot(session, int(user["organization_id"]), created_by=str(user["email"]))
    add_audit(session, int(user["organization_id"]), str(user["email"]), "RECALCULAR", "Analítica de impacto", str(snapshot.id), new_value=f"Puntaje {snapshot.impact_score}/100")
    session.commit()
    set_flash(request, "Analítica de impacto actualizada.")
    return RedirectResponse("/inteligencia-impacto", status_code=303)

@app.post("/inteligencia-impacto/benchmarks/nuevo")
def create_benchmark(
    request: Request, name: str = Form(...), metric_code: str = Form(...), metric_name: str = Form(...),
    period_label: str = Form("Referencia"), unit: str = Form(...), median_value: float = Form(...),
    top_quartile_value: float = Form(...), lower_is_better: str = Form("true"), source_type: str = Form("Referencia interna"),
    source_reference: str = Form(""), confidence_level: str = Form("Media"), notes: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_impact")
    allowed_metrics = {"intensity_employee", "intensity_revenue_billion", "intensity_production", "quality_score", "evidence_coverage"}
    if metric_code not in allowed_metrics or median_value < 0 or top_quartile_value < 0:
        raise HTTPException(400, "Métrica o valores de referencia inválidos")
    org = session.get(Organization, int(user["organization_id"]))
    reference = BenchmarkReference(
        organization_id=org.id, name=name.strip(), sector=org.sector, metric_code=metric_code, metric_name=metric_name.strip(),
        period_label=period_label.strip(), unit=unit.strip(), median_value=median_value, top_quartile_value=top_quartile_value,
        lower_is_better=lower_is_better.lower() in {"1", "true", "si", "sí", "on"}, source_type=source_type.strip(),
        source_reference=source_reference.strip(), confidence_level=confidence_level, notes=notes.strip(), created_by=str(user["email"]),
    )
    session.add(reference)
    add_audit(session, org.id, str(user["email"]), "CREAR", "Benchmark", reference.name, f"{metric_name}: mediana {median_value}; cuartil {top_quartile_value}")
    session.commit()
    set_flash(request, "Referencia de benchmark registrada.")
    return RedirectResponse("/inteligencia-impacto", status_code=303)

@app.post("/inteligencia-impacto/benchmarks/{reference_id}/estado")
def update_benchmark_status(reference_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "manage_impact")
    reference = session.scalar(select(BenchmarkReference).where(BenchmarkReference.id == reference_id, BenchmarkReference.organization_id == int(user["organization_id"])))
    if not reference:
        raise HTTPException(404, "Benchmark no encontrado")
    if status not in {"Activo", "Archivado"}:
        raise HTTPException(400, "Estado inválido")
    reference.status = status
    add_audit(session, reference.organization_id, str(user["email"]), "ACTUALIZAR", "Benchmark", reference.name, new_value=status)
    session.commit()
    set_flash(request, "Estado del benchmark actualizado.")
    return RedirectResponse("/inteligencia-impacto", status_code=303)

@app.get("/inteligencia-impacto/exportar.xlsx")
def export_impact_intelligence(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_impact_view(user)
    organization_id = int(user["organization_id"])
    metrics = impact_metrics(session, organization_id)
    references = list(session.scalars(select(BenchmarkReference).where(BenchmarkReference.organization_id == organization_id)))
    comparisons = compare_benchmarks(metrics, references)
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen de impacto"
    ws.append(["Métrica", "Valor", "Unidad"])
    units = {"total_emissions": "tCO2e", "intensity_employee": "tCO2e/empleado", "intensity_revenue_billion": "tCO2e/mil millones COP", "quality_score": "%", "evidence_coverage": "%", "expected_reduction": "tCO2e", "annual_savings": "COP/año", "value_per_tonne": "COP/tCO2e"}
    for key in ["total_emissions", "intensity_employee", "intensity_revenue_billion", "quality_score", "evidence_coverage", "expected_reduction", "annual_savings", "value_per_tonne"]:
        ws.append([key, metrics.get(key, 0), units[key]])
    ws2 = wb.create_sheet("Benchmark")
    ws2.append(["Referencia", "Métrica", "Actual", "Mediana", "Cuartil superior", "Unidad", "Estado", "Fuente", "Confianza"])
    for row in comparisons:
        ref = row["reference"]
        ws2.append([ref.name, ref.metric_name, row["current"], ref.median_value, ref.top_quartile_value, ref.unit, row["status"], ref.source_reference, ref.confidence_level])
    buffer = BytesIO()
    wb.save(buffer)
    filename = f"inteligencia_impacto_{organization_id}.xlsx"
    return Response(content=buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

def _require_climate_risk_view(user: dict[str, object]) -> None:
    capabilities = user["capabilities"]
    if "view_climate_risk" not in capabilities and "manage_climate_risk" not in capabilities:
        raise HTTPException(403, "Tu rol no tiene acceso a riesgos climáticos")

@app.get("/riesgos-climaticos", response_class=HTMLResponse)
def climate_risk_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_climate_risk_view(user)
    organization_id = int(user["organization_id"])
    summary = assessment_summary(session, organization_id)
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == organization_id).order_by(Inventory.start_date.desc())))
    return templates.TemplateResponse(
        request=request, name="climate_risk.html",
        context=common_context(request, session, user, "climate_risk", summary=summary, inventories=inventories, risk_level=risk_level),
    )

@app.post("/riesgos-climaticos/evaluacion")
def climate_assessment_save(
    request: Request, name: str = Form(...), inventory_id: str = Form(""), methodology: str = Form("Análisis corporativo de escenarios"),
    scenario: str = Form("Escenario central"), base_year: int = Form(...), short_horizon: int = Form(...), medium_horizon: int = Form(...),
    long_horizon: int = Form(...), currency: str = Form("COP"), owner: str = Form(...), status: str = Form("En evaluación"), notes: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    organization_id = int(user["organization_id"])
    if not (base_year <= short_horizon <= medium_horizon <= long_horizon):
        raise HTTPException(400, "Los horizontes deben estar ordenados desde el año base hasta el largo plazo")
    summary = assessment_summary(session, organization_id)
    assessment = summary["assessment"] or ClimateRiskAssessment(organization_id=organization_id, name=name.strip(), created_by=str(user["email"]))
    if not summary["assessment"]:
        session.add(assessment)
    assessment.name = name.strip(); assessment.inventory_id = int(inventory_id) if inventory_id else None
    assessment.methodology = methodology.strip(); assessment.scenario = scenario.strip(); assessment.base_year = base_year
    assessment.short_horizon = short_horizon; assessment.medium_horizon = medium_horizon; assessment.long_horizon = long_horizon
    assessment.currency = currency.strip().upper()[:20]; assessment.owner = owner.strip(); assessment.status = status; assessment.notes = notes.strip()
    refresh_assessment_status(session, assessment, str(user["email"])) if assessment.id else None
    add_audit(session, organization_id, str(user["email"]), "ACTUALIZAR", "Evaluación climática", assessment.name, new_value=assessment.status)
    session.commit(); set_flash(request, "Evaluación climática guardada.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/riesgos/nuevo")
def climate_risk_create(
    request: Request, risk_type: str = Form(...), category: str = Form(...), hazard: str = Form(...), description: str = Form(""),
    location: str = Form("Corporativo"), value_chain_stage: str = Form("Operación propia"), time_horizon: str = Form("Mediano plazo"),
    scenario: str = Form("Escenario central"), likelihood: int = Form(...), financial_impact: int = Form(...), operational_impact: int = Form(...),
    reputational_impact: int = Form(...), control_effectiveness: int = Form(0), financial_exposure: float = Form(0), owner: str = Form(...),
    response_strategy: str = Form("Mitigar"), response_detail: str = Form(""), status: str = Form("Abierto"), source_reference: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    organization_id = int(user["organization_id"]); summary = assessment_summary(session, organization_id)
    assessment = summary["assessment"]
    if not assessment: raise HTTPException(409, "Primero crea la evaluación climática")
    if risk_type not in {"Físico", "Transición", "Oportunidad"}: raise HTTPException(400, "Tipo de riesgo inválido")
    likelihood = max(1, min(5, likelihood)); financial_impact = max(1, min(5, financial_impact))
    operational_impact = max(1, min(5, operational_impact)); reputational_impact = max(1, min(5, reputational_impact))
    inherent, residual = calculate_risk_scores(likelihood, financial_impact, operational_impact, reputational_impact, control_effectiveness)
    risk = ClimateRisk(
        assessment_id=assessment.id, organization_id=organization_id, risk_type=risk_type, category=category.strip(), hazard=hazard.strip(),
        description=description.strip(), location=location.strip(), value_chain_stage=value_chain_stage.strip(), time_horizon=time_horizon,
        scenario=scenario.strip(), likelihood=likelihood, financial_impact=financial_impact, operational_impact=operational_impact,
        reputational_impact=reputational_impact, inherent_score=inherent, control_effectiveness=max(0, min(100, control_effectiveness)),
        residual_score=residual, financial_exposure=max(0, financial_exposure), owner=owner.strip(), response_strategy=response_strategy,
        response_detail=response_detail.strip(), status=status, source_reference=source_reference.strip(), created_by=str(user["email"]),
    )
    session.add(risk); add_audit(session, organization_id, str(user["email"]), "CREAR", "Riesgo climático", risk.hazard, new_value=f"{risk_type} · {risk_level(residual)}")
    session.commit(); set_flash(request, "Riesgo climático registrado.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/riesgos/{risk_id}/actualizar")
def climate_risk_update(
    risk_id: int, request: Request, likelihood: int = Form(...), financial_impact: int = Form(...), operational_impact: int = Form(...),
    reputational_impact: int = Form(...), financial_exposure: float = Form(0), owner: str = Form(...), response_strategy: str = Form(...),
    response_detail: str = Form(""), status: str = Form(...), source_reference: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    risk = session.get(ClimateRisk, risk_id)
    if not risk or risk.organization_id != int(user["organization_id"]): raise HTTPException(404, "Riesgo no encontrado")
    risk.likelihood=max(1,min(5,likelihood)); risk.financial_impact=max(1,min(5,financial_impact)); risk.operational_impact=max(1,min(5,operational_impact)); risk.reputational_impact=max(1,min(5,reputational_impact))
    risk.financial_exposure=max(0, financial_exposure); risk.owner=owner.strip(); risk.response_strategy=response_strategy; risk.response_detail=response_detail.strip(); risk.status=status; risk.source_reference=source_reference.strip()
    synchronize_control_effectiveness(session, risk)
    add_audit(session, risk.organization_id, str(user["email"]), "ACTUALIZAR", "Riesgo climático", risk.hazard, new_value=f"Residual {risk.residual_score}")
    session.commit(); set_flash(request, "Riesgo actualizado.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/controles/nuevo")
def climate_control_create(
    request: Request, risk_id: int = Form(...), name: str = Form(...), control_type: str = Form(...), owner: str = Form(...),
    status: str = Form(...), effectiveness: int = Form(...), implementation_date: str = Form(""), next_review: str = Form(""),
    annual_cost: float = Form(0), evidence: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    organization_id = int(user["organization_id"]); risk = session.get(ClimateRisk, risk_id)
    if not risk or risk.organization_id != organization_id: raise HTTPException(404, "Riesgo no encontrado")
    control = ClimateRiskControl(risk_id=risk.id, organization_id=organization_id, name=name.strip(), control_type=control_type,
        owner=owner.strip(), status=status, effectiveness=max(0, min(100, effectiveness)),
        implementation_date=parse_date(implementation_date) if implementation_date else None, next_review=parse_date(next_review) if next_review else None,
        annual_cost=max(0, annual_cost), evidence=evidence.strip(), created_by=str(user["email"]))
    session.add(control); session.flush(); synchronize_control_effectiveness(session, risk)
    add_audit(session, organization_id, str(user["email"]), "CREAR", "Control climático", control.name, new_value=f"Efectividad {control.effectiveness}%")
    session.commit(); set_flash(request, "Control registrado y riesgo residual recalculado.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/hoja-ruta")
def climate_roadmap_save(
    request: Request, name: str = Form(...), baseline_year: int = Form(...), target_year: int = Form(...), owner: str = Form(...),
    governance: str = Form(""), approved_budget: float = Form(0), status: str = Form(...), notes: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    organization_id = int(user["organization_id"]); summary=assessment_summary(session, organization_id); assessment=summary["assessment"]
    if target_year < baseline_year: raise HTTPException(400, "El año objetivo no puede ser anterior al año base")
    if not assessment: raise HTTPException(409, "Primero crea la evaluación climática")
    roadmap = summary["roadmap"] or ClimateTransitionRoadmap(organization_id=organization_id, assessment_id=assessment.id, name=name.strip(), created_by=str(user["email"]))
    if not summary["roadmap"]: session.add(roadmap)
    roadmap.name=name.strip(); roadmap.baseline_year=baseline_year; roadmap.target_year=target_year; roadmap.owner=owner.strip(); roadmap.governance=governance.strip(); roadmap.approved_budget=max(0, approved_budget); roadmap.status=status; roadmap.notes=notes.strip()
    add_audit(session, organization_id, str(user["email"]), "ACTUALIZAR", "Hoja de ruta climática", roadmap.name, new_value=roadmap.status)
    session.commit(); set_flash(request, "Hoja de ruta guardada.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/acciones/nueva")
def climate_action_create(
    request: Request, risk_id: str = Form(""), category: str = Form(...), title: str = Form(...), description: str = Form(""), owner: str = Form(...),
    start_date: str = Form(""), end_date: str = Form(""), priority: str = Form("Media"), status: str = Form("Planeada"), progress: int = Form(0),
    expected_reduction_tco2e: float = Form(0), capex: float = Form(0), annual_opex: float = Form(0), annual_savings: float = Form(0),
    avoided_loss: float = Form(0), indicator: str = Form(""), target_value: float = Form(0), current_value: float = Form(0), unit: str = Form(""),
    dependencies: str = Form(""), evidence_note: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    organization_id=int(user["organization_id"]); summary=assessment_summary(session, organization_id); roadmap=summary["roadmap"]
    parsed_start = parse_date(start_date) if start_date else None; parsed_end = parse_date(end_date) if end_date else None
    if parsed_start and parsed_end and parsed_end < parsed_start: raise HTTPException(400, "La fecha final no puede ser anterior a la fecha inicial")
    if not roadmap: raise HTTPException(409, "Primero crea la hoja de ruta")
    linked_risk = session.get(ClimateRisk, int(risk_id)) if risk_id else None
    if linked_risk and linked_risk.organization_id != organization_id: raise HTTPException(404, "Riesgo no encontrado")
    action=ClimateTransitionAction(roadmap_id=roadmap.id, organization_id=organization_id, risk_id=linked_risk.id if linked_risk else None,
        category=category.strip(), title=title.strip(), description=description.strip(), owner=owner.strip(), start_date=parsed_start,
        end_date=parsed_end, priority=priority, status=status, progress=max(0,min(100,progress)), expected_reduction_tco2e=max(0,expected_reduction_tco2e),
        capex=max(0,capex), annual_opex=max(0,annual_opex), annual_savings=max(0,annual_savings), avoided_loss=max(0,avoided_loss), indicator=indicator.strip(),
        target_value=target_value, current_value=current_value, unit=unit.strip(), dependencies=dependencies.strip(), evidence_note=evidence_note.strip(), created_by=str(user["email"]))
    session.add(action); add_audit(session, organization_id, str(user["email"]), "CREAR", "Acción climática", action.title, new_value=action.status)
    session.commit(); set_flash(request, "Acción añadida a la hoja de ruta.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.post("/riesgos-climaticos/acciones/{action_id}/estado")
def climate_action_update(
    action_id: int, request: Request, status: str = Form(...), progress: int = Form(...), current_value: float = Form(0), evidence_note: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_risk")
    action=session.get(ClimateTransitionAction, action_id)
    if not action or action.organization_id != int(user["organization_id"]): raise HTTPException(404, "Acción no encontrada")
    action.status=status; action.progress=max(0,min(100,progress)); action.current_value=current_value; action.evidence_note=evidence_note.strip()
    add_audit(session, action.organization_id, str(user["email"]), "ACTUALIZAR", "Acción climática", action.title, new_value=f"{status} · {action.progress}%")
    session.commit(); set_flash(request, "Avance de la acción actualizado.")
    return RedirectResponse("/riesgos-climaticos", status_code=303)

@app.get("/riesgos-climaticos/exportar.xlsx")
def climate_risk_export(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_climate_risk_view(user); organization_id=int(user["organization_id"]); summary=assessment_summary(session, organization_id)
    wb=Workbook(); ws=wb.active; ws.title="Resumen"
    ws.append(["Evaluación", summary["assessment"].name if summary["assessment"] else ""]); ws.append(["Riesgos", summary["counts"]["total"]]); ws.append(["Exposición bruta", summary["financial"]["gross_exposure"]]); ws.append(["Exposición residual", summary["financial"]["residual_exposure"]]); ws.append(["Exposición evitada", summary["financial"]["avoided_exposure"]]); ws.append(["Valor de oportunidades", summary["financial"]["opportunity_value"]]); ws.append(["Costo anual de controles", summary["financial"]["control_cost"]]); ws.append(["Preparación", summary["readiness_score"]])
    ws2=wb.create_sheet("Riesgos"); ws2.append(["Tipo","Categoría","Riesgo u oportunidad","Ubicación","Horizonte","Probabilidad","Impacto máximo","Inherente","Controles %","Residual","Nivel","Exposición","Responsable","Estrategia","Estado","Fuente"])
    for risk in summary["risks"]: ws2.append([risk.risk_type,risk.category,risk.hazard,risk.location,risk.time_horizon,risk.likelihood,max(risk.financial_impact,risk.operational_impact,risk.reputational_impact),risk.inherent_score,risk.control_effectiveness,risk.residual_score,risk_level(risk.residual_score),risk.financial_exposure,risk.owner,risk.response_strategy,risk.status,risk.source_reference])
    ws3=wb.create_sheet("Controles"); ws3.append(["Riesgo","Control","Tipo","Responsable","Estado","Efectividad %","Costo anual","Próxima revisión","Evidencia"])
    risk_map={risk.id:risk.hazard for risk in summary["risks"]}
    for control in summary["controls"]: ws3.append([risk_map.get(control.risk_id,""),control.name,control.control_type,control.owner,control.status,control.effectiveness,control.annual_cost,control.next_review,control.evidence])
    ws4=wb.create_sheet("Hoja de ruta"); ws4.append(["Categoría","Acción","Riesgo vinculado","Responsable","Inicio","Fin","Prioridad","Estado","Avance %","Reducción tCO2e","CAPEX","OPEX anual","Ahorro anual","Pérdida evitada","Indicador","Meta","Actual","Unidad","Dependencias"])
    for action in summary["actions"]: ws4.append([action.category,action.title,risk_map.get(action.risk_id,""),action.owner,action.start_date,action.end_date,action.priority,action.status,action.progress,action.expected_reduction_tco2e,action.capex,action.annual_opex,action.annual_savings,action.avoided_loss,action.indicator,action.target_value,action.current_value,action.unit,action.dependencies])
    buffer=BytesIO(); wb.save(buffer)
    return Response(content=buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="riesgos_climaticos_{organization_id}.xlsx"'})

def _require_climate_disclosure_view(user: dict[str, object]) -> None:
    capabilities = user["capabilities"]
    if "view_climate_disclosure" not in capabilities and "manage_climate_disclosure" not in capabilities:
        raise HTTPException(403, "Tu rol no tiene acceso a divulgación climática")

@app.get("/divulgacion-climatica", response_class=HTMLResponse)
def climate_disclosure_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_climate_disclosure_view(user)
    organization_id = int(user["organization_id"])
    comparison = scenario_comparison(session, organization_id)
    disclosure = disclosure_summary(session, organization_id)
    board = board_summary(session, organization_id)
    inventories = list(session.scalars(
        select(Inventory).where(Inventory.organization_id == organization_id).order_by(Inventory.start_date.desc())
    ))
    return templates.TemplateResponse(
        request=request, name="climate_disclosure.html",
        context=common_context(
            request, session, user, "climate_disclosure", comparison=comparison,
            disclosure=disclosure, board=board, inventories=inventories, today=date.today(),
        ),
    )

@app.post("/divulgacion-climatica/escenarios/nuevo")
def climate_scenario_create(
    request: Request, name: str = Form(...), code: str = Form(...), scenario_type: str = Form(...),
    temperature_pathway: str = Form("No especificada"), physical_multiplier: float = Form(1.0),
    transition_multiplier: float = Form(1.0), opportunity_multiplier: float = Form(1.0),
    carbon_price_2030: float = Form(0), energy_cost_change_pct: float = Form(0),
    demand_change_pct: float = Form(0), probability_weight: float = Form(0), narrative: str = Form(""),
    source_reference: str = Form(""), status: str = Form("Activo"),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    organization_id = int(user["organization_id"])
    normalized_code = code.strip().upper()[:40]
    duplicate = session.scalar(select(ClimateScenarioDefinition).where(
        ClimateScenarioDefinition.organization_id == organization_id,
        ClimateScenarioDefinition.code == normalized_code,
    ))
    if duplicate:
        raise HTTPException(409, "Ya existe un escenario con ese código")
    comparison = scenario_comparison(session, organization_id)
    assessment = comparison["risk_summary"]["assessment"]
    scenario = ClimateScenarioDefinition(
        organization_id=organization_id, assessment_id=assessment.id if assessment else None,
        name=name.strip(), code=normalized_code, scenario_type=scenario_type.strip(),
        temperature_pathway=temperature_pathway.strip(), physical_multiplier=max(0.1, min(3.0, physical_multiplier)),
        transition_multiplier=max(0.1, min(3.0, transition_multiplier)),
        opportunity_multiplier=max(0.1, min(3.0, opportunity_multiplier)),
        carbon_price_2030=max(0, carbon_price_2030), energy_cost_change_pct=max(-100, min(500, energy_cost_change_pct)),
        demand_change_pct=max(-100, min(500, demand_change_pct)), probability_weight=max(0, min(100, probability_weight)),
        narrative=narrative.strip(), source_reference=source_reference.strip(), status=status, created_by=str(user["email"]),
    )
    session.add(scenario)
    add_audit(session, organization_id, str(user["email"]), "CREAR", "Escenario climático", scenario.name, new_value=scenario.code)
    session.commit(); set_flash(request, "Escenario climático registrado.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/escenarios/{scenario_id}/actualizar")
def climate_scenario_update(
    scenario_id: int, request: Request, physical_multiplier: float = Form(...), transition_multiplier: float = Form(...),
    opportunity_multiplier: float = Form(...), carbon_price_2030: float = Form(0),
    energy_cost_change_pct: float = Form(0), demand_change_pct: float = Form(0),
    probability_weight: float = Form(0), narrative: str = Form(""), source_reference: str = Form(""),
    status: str = Form("Activo"), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    scenario = session.get(ClimateScenarioDefinition, scenario_id)
    if not scenario or scenario.organization_id != int(user["organization_id"]):
        raise HTTPException(404, "Escenario no encontrado")
    scenario.physical_multiplier = max(0.1, min(3.0, physical_multiplier))
    scenario.transition_multiplier = max(0.1, min(3.0, transition_multiplier))
    scenario.opportunity_multiplier = max(0.1, min(3.0, opportunity_multiplier))
    scenario.carbon_price_2030 = max(0, carbon_price_2030)
    scenario.energy_cost_change_pct = max(-100, min(500, energy_cost_change_pct))
    scenario.demand_change_pct = max(-100, min(500, demand_change_pct))
    scenario.probability_weight = max(0, min(100, probability_weight))
    scenario.narrative = narrative.strip(); scenario.source_reference = source_reference.strip(); scenario.status = status
    add_audit(session, scenario.organization_id, str(user["email"]), "ACTUALIZAR", "Escenario climático", scenario.name, new_value=f"Peso {scenario.probability_weight}%")
    session.commit(); set_flash(request, "Supuestos del escenario actualizados.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/declaracion")
def climate_disclosure_save(
    request: Request, title: str = Form(...), inventory_id: str = Form(""), framework: str = Form(...),
    reporting_period: str = Form(...), scope_description: str = Form(""), materiality_basis: str = Form(""),
    owner: str = Form(...), status: str = Form("Borrador"), notes: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    organization_id = int(user["organization_id"])
    summary = disclosure_summary(session, organization_id)
    statement = summary["statement"] or ClimateDisclosureStatement(organization_id=organization_id, title=title.strip(), created_by=str(user["email"]))
    if not summary["statement"]:
        session.add(statement)
    statement.title = title.strip(); statement.inventory_id = int(inventory_id) if inventory_id else None
    statement.framework = framework.strip(); statement.reporting_period = reporting_period.strip()
    statement.scope_description = scope_description.strip(); statement.materiality_basis = materiality_basis.strip()
    statement.owner = owner.strip(); statement.status = status; statement.notes = notes.strip()
    if status == "Aprobada":
        ensure_capability(user, "approve")
        statement.approved_by = str(user["email"]); statement.approved_at = datetime.now(UTC)
    add_audit(session, organization_id, str(user["email"]), "ACTUALIZAR", "Divulgación climática", statement.title, new_value=status)
    session.commit(); set_flash(request, "Ficha de divulgación guardada.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/requisitos/nuevo")
def climate_requirement_create(
    request: Request, pillar: str = Form(...), code: str = Form(...), requirement: str = Form(...),
    response: str = Form(""), status: str = Form("Pendiente"), evidence_reference: str = Form(""),
    owner: str = Form(...), due_date: str = Form(""), session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    organization_id = int(user["organization_id"]); summary = disclosure_summary(session, organization_id)
    if status not in {"Completo", "Parcial", "Pendiente", "No aplica"}:
        raise HTTPException(400, "Estado de requisito inválido")
    statement = summary["statement"]
    if not statement:
        raise HTTPException(409, "Primero crea la ficha de divulgación")
    normalized_code = code.strip().upper()[:40]
    duplicate = session.scalar(select(ClimateDisclosureRequirement).where(
        ClimateDisclosureRequirement.statement_id == statement.id,
        ClimateDisclosureRequirement.code == normalized_code,
    ))
    if duplicate:
        raise HTTPException(409, "Ya existe un requisito con ese código")
    item = ClimateDisclosureRequirement(
        statement_id=statement.id, organization_id=organization_id, pillar=pillar.strip(), code=normalized_code,
        requirement=requirement.strip(), response=response.strip(), status=status,
        evidence_reference=evidence_reference.strip(), owner=owner.strip(),
        due_date=parse_date(due_date) if due_date else None, updated_by=str(user["email"]),
    )
    session.add(item); add_audit(session, organization_id, str(user["email"]), "CREAR", "Requisito de divulgación", item.code, new_value=item.pillar)
    session.commit(); set_flash(request, "Requisito de divulgación registrado.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/requisitos/{requirement_id}/actualizar")
def climate_requirement_update(
    requirement_id: int, request: Request, response: str = Form(""), status: str = Form(...),
    evidence_reference: str = Form(""), owner: str = Form(...), due_date: str = Form(""),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    requirement = session.get(ClimateDisclosureRequirement, requirement_id)
    if not requirement or requirement.organization_id != int(user["organization_id"]):
        raise HTTPException(404, "Requisito no encontrado")
    if status not in {"Completo", "Parcial", "Pendiente", "No aplica"}:
        raise HTTPException(400, "Estado de requisito inválido")
    requirement.response = response.strip(); requirement.status = status
    requirement.evidence_reference = evidence_reference.strip(); requirement.owner = owner.strip()
    requirement.due_date = parse_date(due_date) if due_date else None; requirement.updated_by = str(user["email"])
    add_audit(session, requirement.organization_id, str(user["email"]), "ACTUALIZAR", "Requisito de divulgación", requirement.code, new_value=status)
    session.commit(); set_flash(request, "Requisito de divulgación actualizado.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/comite")
def climate_board_save(
    request: Request, title: str = Form(...), meeting_date: str = Form(""), audience: str = Form("Comité directivo"),
    status: str = Form("Borrador"), executive_summary: str = Form(""), decisions_required: str = Form(""),
    key_message: str = Form(""), prepared_by: str = Form(...),
    session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    organization_id = int(user["organization_id"])
    summary = board_summary(session, organization_id)
    briefing = summary["briefing"] or ClimateBoardBriefing(organization_id=organization_id, title=title.strip(), created_by=str(user["email"]))
    if not summary["briefing"]:
        session.add(briefing)
    risk_assessment = summary["risk_summary"]["assessment"]
    statement = summary["disclosure"]["statement"]
    briefing.assessment_id = risk_assessment.id if risk_assessment else None
    briefing.disclosure_id = statement.id if statement else None
    briefing.title = title.strip(); briefing.meeting_date = parse_date(meeting_date) if meeting_date else None
    briefing.audience = audience.strip(); briefing.status = status; briefing.executive_summary = executive_summary.strip()
    briefing.decisions_required = decisions_required.strip(); briefing.key_message = key_message.strip(); briefing.prepared_by = prepared_by.strip()
    if status == "Aprobado":
        ensure_capability(user, "approve")
        briefing.approved_by = str(user["email"]); briefing.approved_at = datetime.now(UTC)
    add_audit(session, organization_id, str(user["email"]), "ACTUALIZAR", "Informe de comité", briefing.title, new_value=status)
    session.commit(); set_flash(request, "Informe para comité actualizado.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/decisiones/nueva")
def climate_board_decision_create(
    request: Request, topic: str = Form(...), decision: str = Form(""), owner: str = Form(...),
    due_date: str = Form(""), status: str = Form("Pendiente"), rationale: str = Form(""),
    evidence_reference: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    organization_id = int(user["organization_id"]); summary = board_summary(session, organization_id)
    briefing = summary["briefing"]
    if not briefing:
        raise HTTPException(409, "Primero crea el informe para comité")
    item = ClimateBoardDecision(
        briefing_id=briefing.id, organization_id=organization_id, topic=topic.strip(), decision=decision.strip(),
        owner=owner.strip(), due_date=parse_date(due_date) if due_date else None, status=status,
        rationale=rationale.strip(), evidence_reference=evidence_reference.strip(), created_by=str(user["email"]),
    )
    session.add(item); add_audit(session, organization_id, str(user["email"]), "CREAR", "Decisión de comité", item.topic, new_value=status)
    session.commit(); set_flash(request, "Decisión registrada.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.post("/divulgacion-climatica/decisiones/{decision_id}/estado")
def climate_board_decision_update(
    decision_id: int, request: Request, decision: str = Form(""), owner: str = Form(...),
    due_date: str = Form(""), status: str = Form(...), rationale: str = Form(""),
    evidence_reference: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_climate_disclosure")
    item = session.get(ClimateBoardDecision, decision_id)
    if not item or item.organization_id != int(user["organization_id"]):
        raise HTTPException(404, "Decisión no encontrada")
    item.decision = decision.strip(); item.owner = owner.strip(); item.due_date = parse_date(due_date) if due_date else None
    item.status = status; item.rationale = rationale.strip(); item.evidence_reference = evidence_reference.strip()
    add_audit(session, item.organization_id, str(user["email"]), "ACTUALIZAR", "Decisión de comité", item.topic, new_value=status)
    session.commit(); set_flash(request, "Estado de la decisión actualizado.")
    return RedirectResponse("/divulgacion-climatica", status_code=303)

@app.get("/divulgacion-climatica/exportar.xlsx")
def climate_disclosure_export(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_climate_disclosure_view(user)
    organization_id = int(user["organization_id"])
    comparison = scenario_comparison(session, organization_id); disclosure = disclosure_summary(session, organization_id); board = board_summary(session, organization_id)
    wb = Workbook(); ws = wb.active; ws.title = "Comparación"
    ws.append(["Escenario", "Código", "Trayectoria", "Probabilidad %", "Exposición", "Costo carbono", "Oportunidad", "Presión neta", "Presión ponderada", "Resiliencia", "Riesgos críticos"])
    for result in comparison["results"]:
        scenario = result["scenario"]
        ws.append([scenario.name, scenario.code, scenario.temperature_pathway, scenario.probability_weight, result["downside_exposure"], result["carbon_cost"], result["opportunity_value"], result["net_financial_pressure"], result["weighted_pressure"], result["resilience_score"], result["critical_risks"]])
    ws2 = wb.create_sheet("Supuestos"); ws2.append(["Escenario", "Tipo", "Multiplicador físico", "Multiplicador transición", "Multiplicador oportunidad", "Precio carbono 2030", "Cambio energía %", "Cambio demanda %", "Narrativa", "Fuente", "Estado"])
    for scenario in comparison["scenarios"]:
        ws2.append([scenario.name, scenario.scenario_type, scenario.physical_multiplier, scenario.transition_multiplier, scenario.opportunity_multiplier, scenario.carbon_price_2030, scenario.energy_cost_change_pct, scenario.demand_change_pct, scenario.narrative, scenario.source_reference, scenario.status])
    ws3 = wb.create_sheet("Divulgación"); ws3.append(["Pilar", "Código", "Requisito", "Respuesta", "Estado", "Evidencia", "Responsable", "Vencimiento"])
    for requirement in disclosure["requirements"]:
        ws3.append([requirement.pillar, requirement.code, requirement.requirement, requirement.response, requirement.status, requirement.evidence_reference, requirement.owner, requirement.due_date])
    ws4 = wb.create_sheet("Decisiones"); ws4.append(["Tema", "Decisión", "Responsable", "Vencimiento", "Estado", "Justificación", "Evidencia"])
    for item in board["decisions"]:
        ws4.append([item.topic, item.decision, item.owner, item.due_date, item.status, item.rationale, item.evidence_reference])
    buffer = BytesIO(); wb.save(buffer)
    return Response(content=buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="divulgacion_climatica_{organization_id}.xlsx"'})

@app.get("/divulgacion-climatica/comite.pdf")
def climate_board_pdf(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    _require_climate_disclosure_view(user)
    organization_id = int(user["organization_id"]); org = session.get(Organization, organization_id)
    summary = board_summary(session, organization_id)
    content, digest = build_board_pdf(summary, org.name)
    briefing = summary["briefing"]
    if briefing:
        briefing.document_hash = digest
        session.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="informe_comite_climatico_{organization_id}.pdf"', "X-Document-SHA256": digest})

@app.get("/consolidacion", response_class=HTMLResponse)
def consolidation_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "view_consolidation")
    summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
    architecture = domain_architecture_summary(app, BASE_DIR.parent)
    return templates.TemplateResponse(
        request=request,
        name="consolidation.html",
        context=common_context(
            request,
            session,
            user,
            "consolidation",
            summary=summary,
            domain_architecture=architecture,
        ),
    )

@app.post("/consolidacion/hallazgos/{finding_id}")
def update_consolidation_finding(
    finding_id: int,
    request: Request,
    status: str = Form(...),
    owner: str = Form(""),
    target_version: str = Form("V1.0"),
    evidence: str = Form(""),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_consolidation")
    finding = session.scalar(select(ConsolidationFinding).where(
        ConsolidationFinding.id == finding_id,
        ConsolidationFinding.organization_id == int(user["organization_id"]),
    ))
    if not finding:
        raise HTTPException(404, "Hallazgo no encontrado")
    if status not in {"Abierto", "En curso", "Bloqueado", "Resuelto", "Aceptado"}:
        raise HTTPException(400, "Estado inválido")
    previous = finding.status
    finding.status = status
    finding.owner = owner.strip() or finding.owner
    finding.target_version = target_version.strip() or finding.target_version
    finding.evidence = evidence.strip()
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Hallazgo de consolidación", finding.code, previous_value=previous, new_value=status, detail=finding.title)
    session.commit()
    set_flash(request, f"Hallazgo {finding.code} actualizado.")
    return RedirectResponse("/consolidacion#hallazgos", status_code=303)

@app.post("/consolidacion/puertas/{gate_id}")
def update_release_gate(
    gate_id: int,
    request: Request,
    status: str = Form(...),
    responsible: str = Form(""),
    evidence: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_consolidation")
    gate = session.scalar(select(ReleaseGate).where(
        ReleaseGate.id == gate_id,
        ReleaseGate.organization_id == int(user["organization_id"]),
    ))
    if not gate:
        raise HTTPException(404, "Puerta de salida no encontrada")
    if status not in {"Pendiente", "Parcial", "En revisión", "Aprobado", "Bloqueado"}:
        raise HTTPException(400, "Estado inválido")
    previous = gate.status
    gate.status = status
    gate.responsible = responsible.strip() or gate.responsible
    gate.evidence = evidence.strip()
    gate.notes = notes.strip()
    add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Puerta V1.0", gate.code, previous_value=previous, new_value=status, detail=gate.name)
    session.commit()
    set_flash(request, f"Puerta {gate.code} actualizada.")
    return RedirectResponse("/consolidacion#puertas", status_code=303)

@app.post("/consolidacion/recorridos/{validation_id}")
def update_journey_validation(
    validation_id: int,
    request: Request,
    status: str = Form(...),
    notes: str = Form(""),
    session: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    ensure_capability(user, "manage_consolidation")
    validation = session.scalar(select(JourneyValidation).where(
        JourneyValidation.id == validation_id,
        JourneyValidation.organization_id == int(user["organization_id"]),
    ))
    if not validation:
        raise HTTPException(404, "Recorrido no encontrado")
    if status not in {"No probado", "En prueba", "Con bloqueos", "Aprobado"}:
        raise HTTPException(400, "Estado inválido")
    previous = validation.status
    validation.status = status
    validation.notes = notes.strip()
    validation.tested_by = str(user["email"]) if status != "No probado" else ""
    validation.tested_at = datetime.now(UTC) if status != "No probado" else None
    add_audit(session, int(user["organization_id"]), str(user["email"]), "VALIDAR", "Recorrido por rol", validation.journey_code, previous_value=previous, new_value=status, detail=validation.notes)
    session.commit()
    set_flash(request, f"Recorrido {validation.journey_code} actualizado.")
    return RedirectResponse("/consolidacion#recorridos", status_code=303)

@app.get("/consolidacion/exportar.xlsx")
def export_consolidation(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "view_consolidation")
    summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
    content = build_consolidation_workbook(summary)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="consolidacion_v1_0.xlsx"'},
    )

@app.get("/api/arquitectura/resumen")
def architecture_api(user: dict = Depends(require_user)):
    ensure_capability(user, "view_consolidation")
    return domain_architecture_summary(app, BASE_DIR.parent)

@app.get("/api/consolidacion/resumen")
def consolidation_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
    ensure_capability(user, "view_consolidation")
    summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
    return Response(content=summary_json(summary), media_type="application/json")

register_public_routes(app, templates, current_user)
register_auth_routes(app, templates, current_user)

register_organization_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_information_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    parse_date, get_inventory, ensure_inventory_editable, quality_from, safe_filename,
    format_bytes, ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE, ALLOWED_UNITS,
    DATA_ORIGINS, _parse_excel_period,
)
register_capture_routes(
    app, templates, common_context, require_user, set_flash,
    parse_date, get_inventory, ensure_inventory_editable, quality_from, safe_filename,
    ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE, ALLOWED_UNITS, DATA_ORIGINS,
)
register_review_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    parse_date, get_inventory, get_source_for_user, ensure_inventory_editable,
    review_gate_summary, clone_inventory_version,
)

register_user_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_service_operations_routes(
    app, templates, common_context, require_user, ensure_capability
)
register_inventory_routes(
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
    ALLOWED_UNITS,
    DATA_ORIGINS,
)
register_sectorization_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, ensure_inventory_editable,
)
register_calculation_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, ensure_inventory_editable,
)
register_methodology_admin_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, ALLOWED_UNITS
)
register_supply_chain_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    parse_date, get_inventory, ensure_inventory_editable, safe_filename,
    ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE,
)
register_support_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_commercial_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_payment_routes(app, templates)
register_commercial_operations_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, format_number
)
register_customer_success_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_report_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory
)
register_reduction_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    parse_date, get_inventory, get_source_for_user, ensure_inventory_editable, inventory_metrics,
)
register_delivery_routes(
    app, templates, common_context, require_user, get_inventory
)
register_workflow_routes(
    app, templates, common_context, require_user
)
register_experience_routes(
    app, templates, common_context, require_user, get_inventory
)
register_legal_routes(
    app, templates, current_user
)

register_methodology_core_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_factor_library_routes(
    app, templates, common_context, require_user, ensure_capability
)
register_methodology_closure_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory, ensure_inventory_editable
)
register_land_removals_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory, ensure_inventory_editable
)

register_product_project_assurance_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory, ensure_inventory_editable
)

register_colombia_library_routes(
    app, templates, common_context, require_user, ensure_capability
)

register_pilot_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)

register_pilot_execution_routes(
    app, templates, common_context, require_user, set_flash
)

register_data_quality_routes(
    app, templates, common_context, require_user, set_flash
)
register_period_close_routes(
    app, templates, common_context, require_user, set_flash
)
register_operational_import_routes(
    app, templates, common_context, require_user, set_flash, INSTANCE_DIR, MAX_UPLOAD_SIZE
)
register_integration_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    ensure_inventory_editable, ALLOWED_UNITS,
)
register_operations_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_demo_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_product_intelligence_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, settings
)
register_guided_onboarding_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)

@app.get("/modulos", response_class=HTMLResponse)
def modules_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
    return templates.TemplateResponse(
        request=request,
        name="modules.html",
        context=common_context(request, session, user, "modules", modules=PRODUCT_MODULES),
    )

@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version, "environment": settings.environment}

@app.get("/api/ready")
def ready():
    snapshot = diagnostic_snapshot()
    status_code = 200 if snapshot["status"] == "ready" else 503
    return Response(
        content=json.dumps(snapshot, ensure_ascii=False, default=str),
        media_type="application/json",
        status_code=status_code,
    )
