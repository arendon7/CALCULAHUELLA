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
from .saas_admin_web import register_saas_admin_routes
from .impact_intelligence_web import register_impact_intelligence_routes
from .climate_risk_web import register_climate_risk_routes
from .climate_disclosure_web import register_climate_disclosure_routes
from .consolidation_web import register_consolidation_routes
from .analytics_web import register_analytics_routes
from .scenarios_web import register_scenario_routes
from .verification_web import register_verification_routes
from .automations_web import register_automation_routes
from .service_account_web import register_service_account_routes
from .customer_onboarding_web import register_customer_onboarding_routes
from .platform_admin_web import register_platform_admin_routes
from .document_center_web import register_document_center_routes
from .readiness_web import register_readiness_routes
from .notifications_web import register_notification_routes
from .portfolio_web import register_portfolio_routes
from .executive_portfolio_web import register_executive_portfolio_routes
from .compliance_web import register_compliance_routes
from .methodology_governance_web import register_methodology_governance_routes
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
register_saas_admin_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_impact_intelligence_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_climate_risk_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_climate_disclosure_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_consolidation_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_analytics_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date,
    get_inventory, ensure_inventory_editable
)
register_scenario_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, ensure_inventory_editable
)
register_verification_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, review_gate_summary
)
register_automation_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory
)
register_service_account_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_customer_onboarding_routes(
    app, templates, common_context, require_user, set_flash, parse_date, get_inventory
)
register_platform_admin_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_document_center_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, get_inventory
)
register_readiness_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
)
register_notification_routes(
    app, templates, common_context, require_user, set_flash
)
register_portfolio_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
)
register_executive_portfolio_routes(
    app, templates, common_context, require_user, ensure_capability
)
register_compliance_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory
)
register_methodology_governance_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, get_inventory
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
