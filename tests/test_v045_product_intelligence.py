from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.architecture import domain_architecture_summary
from app.database import (
    Base,
    CommercialLead,
    DiagnosticAssessment,
    ENGINE,
    ImplementationPlan,
    Organization,
    OrganizationCarbonProfile,
    SessionLocal,
    init_db,
)
from app.main import app
from app.services.product_intelligence import assess_company


@pytest.fixture(autouse=True)
def fresh_database_v045():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v045_scoring_engine_recommends_different_depths_explainably():
    essential = assess_company({
        "employees_band": "1 a 10",
        "facilities_count": 1,
        "countries_count": 1,
        "desired_scopes": "Alcances 1 y 2",
        "objective": "Conocer la huella corporativa",
        "data_availability": "Media",
        "evidence_readiness": "Media",
        "reporting_frequency": "Anual",
    })
    advanced = assess_company({
        "employees_band": "Más de 200",
        "facilities_count": 8,
        "countries_count": 2,
        "sector": "Manufactura química",
        "desired_scopes": "Alcances 1, 2 y 3 avanzado",
        "objective": "Preparación para verificación",
        "assurance_ambition": "Preparación para verificación razonable",
        "data_availability": "Alta",
        "evidence_readiness": "Media",
        "reporting_frequency": "Mensual",
        "has_fleet": True,
        "uses_fuels": True,
        "uses_refrigerants": True,
        "manages_waste": True,
        "has_wastewater": True,
        "relies_on_suppliers": True,
        "has_process_emissions": True,
    })
    assert essential.package_code == "ESENCIAL"
    assert advanced.package_code == "CORPORATIVO"
    assert advanced.total_score > essential.total_score
    assert "Alcance 3 avanzado" in advanced.recommended_scopes
    assert "Portal del verificador" in advanced.applicable_modules
    assert advanced.probable_sources and advanced.next_steps


def test_v045_demo_companies_have_approved_profiles_diagnoses_and_plans():
    with SessionLocal() as session:
        demo_names = [
            "Greenatics", "Industrias Andinas", "Café Sierra Verde",
            "Ruta Norte Logística", "Hotel Bosque Azul",
        ]
        organizations = list(session.scalars(select(Organization).where(Organization.trade_name.in_(demo_names))))
        assert len(organizations) == 5
        for organization in organizations:
            profile = session.scalar(select(OrganizationCarbonProfile).where(OrganizationCarbonProfile.organization_id == organization.id))
            assessment = session.scalar(select(DiagnosticAssessment).where(DiagnosticAssessment.organization_id == organization.id).order_by(DiagnosticAssessment.id.desc()))
            plan = session.scalar(select(ImplementationPlan).where(ImplementationPlan.organization_id == organization.id).order_by(ImplementationPlan.id.desc()))
            assert profile is not None and profile.profile_completion >= 80 and profile.status == "Completo"
            assert assessment is not None and assessment.status == "Aprobado" and assessment.assessment_version == "V0.45"
            assert assessment.recommended_package_code in {"EMPRESARIAL", "CORPORATIVO"}
            assert plan is not None and plan.status == "Aprobado" and len(plan.items) >= 6


def test_v045_public_diagnostic_persists_lead_and_explainable_assessment():
    with TestClient(app) as client:
        page = client.get("/diagnostico")
        assert page.status_code == 200
        assert "Profundidad" in page.text or "diagnóstico" in page.text.lower()
        response = client.post(
            "/diagnostico",
            data={
                "company_name": "Química Circular S.A.S.",
                "contact_name": "Ana Pérez",
                "email": "ana@quimicacircular.test",
                "sector": "Manufactura química",
                "employees_band": "51 a 200",
                "facilities_count": "3",
                "countries_count": "1",
                "desired_scopes": "Alcances 1, 2 y 3 priorizado",
                "objective": "Preparación para verificación",
                "urgency": "Alta",
                "deadline_months": "5",
                "data_availability": "Media",
                "evidence_readiness": "Parcial",
                "reporting_frequency": "Mensual",
                "assurance_ambition": "Preparación para verificación limitada",
                "has_fleet": "on",
                "uses_fuels": "on",
                "uses_refrigerants": "on",
                "relies_on_suppliers": "on",
                "core_processes": "Producción, reacción química, almacenamiento",
                "current_data_systems": "ERP, Excel",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        thanks = client.get(response.headers["location"])
        assert thanks.status_code == 200
        assert "Gestión" in thanks.text and "Alcance" in thanks.text
    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).where(CommercialLead.email == "ana@quimicacircular.test"))
        assessment = session.scalar(select(DiagnosticAssessment).where(DiagnosticAssessment.lead_id == lead.id))
        assert lead is not None and assessment is not None
        assert lead.recommended_plan_code == assessment.recommended_package_code
        assert json.loads(assessment.probable_sources_json)
        assert json.loads(assessment.next_steps_json)


def test_v045_internal_profile_assessment_and_plan_workflow():
    with TestClient(app) as client:
        login(client)
        page = client.get("/inteligencia-producto")
        assert page.status_code == 200
        assert "Perfil, diagnóstico y ruta" in page.text
        profile = client.post(
            "/inteligencia-producto/perfil",
            data={
                "company_size": "Mediana",
                "business_model": "Manufactura y distribución",
                "sector_subsector": "Manufactura industrial",
                "operating_description": "Producción, almacenamiento y distribución en tres sedes.",
                "countries_count": "1",
                "countries": "Colombia",
                "facility_types": "Planta, bodega, oficina",
                "core_processes": "Producción, generación de vapor, distribución",
                "energy_sources": "Electricidad, diésel, gas natural",
                "fleet_profile": "Flota propia y transporte contratado",
                "refrigerants_profile": "Equipos con registro de recargas",
                "waste_profile": "Residuos aprovechables y de proceso",
                "wastewater_profile": "Vertimientos industriales",
                "agriculture_land_use_profile": "No aplica",
                "key_materials": "Acero, químicos, empaques",
                "supplier_profile": "Proveedores estratégicos y logística",
                "reporting_drivers": "Clientes, sostenibilidad, verificación",
                "climate_goals": "Reducir 20% al 2030",
                "current_data_systems": "ERP, Excel",
                "inventory_history": "Serie histórica",
                "data_availability": "Alta",
                "evidence_readiness": "Media",
                "reporting_frequency": "Mensual",
                "assurance_ambition": "Preparación para verificación razonable",
                "inventory_owner": "Coordinación ambiental",
                "executive_sponsor": "Gerencia de operaciones",
            },
            follow_redirects=False,
        )
        assert profile.status_code == 303
        assessment_response = client.post(
            "/inteligencia-producto/evaluar",
            data={
                "desired_scopes": "Alcances 1, 2 y 3 avanzado",
                "objective": "Preparación para verificación",
                "urgency": "Alta",
                "deadline_months": "6",
            },
            follow_redirects=False,
        )
        assert assessment_response.status_code == 303
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).where(Organization.trade_name == "Industrias Andinas"))
        assessment = session.scalar(select(DiagnosticAssessment).where(DiagnosticAssessment.organization_id == organization.id).order_by(DiagnosticAssessment.id.desc()))
        assessment_id = assessment.id
    with TestClient(app) as client:
        login(client)
        approved = client.post(
            f"/inteligencia-producto/evaluaciones/{assessment_id}/aprobar",
            data={"notes": "Aprobado con revisión humana"},
            follow_redirects=False,
        )
        assert approved.status_code == 303
        planned = client.post(
            f"/inteligencia-producto/evaluaciones/{assessment_id}/plan",
            data={"owner": "Coordinación ambiental", "start_date": "2026-09-01"},
            follow_redirects=False,
        )
        assert planned.status_code == 303
        final_page = client.get("/inteligencia-producto")
        assert final_page.status_code == 200
        assert "Aprobado por" in final_page.text
        assert "Implementación controlada" in final_page.text
    with SessionLocal() as session:
        assessment = session.get(DiagnosticAssessment, assessment_id)
        plan = session.scalar(select(ImplementationPlan).where(ImplementationPlan.assessment_id == assessment_id))
        assert assessment.status == "Aprobado"
        assert assessment.approval_notes == "Aprobado con revisión humana"
        assert plan is not None and len(plan.items) >= 6


def test_v045_api_and_architecture_expose_product_intelligence_domain():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        login(client)
        payload = client.get("/api/inteligencia-producto/resumen").json()
        assert payload["version"] == "1.0.0"
        assert payload["profile_completion"] >= 80
        assert payload["assessment"]["package_label"]
        assert payload["plan_count"] >= 1
    summary = domain_architecture_summary(app, Path(__file__).resolve().parents[1])
    domains = {item["code"]: item for item in summary["domains"]}
    assert domains["product_intelligence"]["route_count"] == 8
    assert summary["domain_count"] == 15
    assert summary["persistence"]["model_class_count"] == 120
    assert summary["persistence"]["repository_count"] == 5
    assert summary["persistence"]["service_count"] == 5
    assert summary["duplicate_paths"] == []


def test_v045_demo_repair_is_idempotent_and_does_not_duplicate_plans():
    from app.services.product_intelligence import ensure_demo_product_intelligence

    with SessionLocal() as session:
        before = (
            session.query(OrganizationCarbonProfile).count(),
            session.query(DiagnosticAssessment).count(),
            session.query(ImplementationPlan).count(),
        )
        first = ensure_demo_product_intelligence(session)
        second = ensure_demo_product_intelligence(session)
        session.commit()
        after = (
            session.query(OrganizationCarbonProfile).count(),
            session.query(DiagnosticAssessment).count(),
            session.query(ImplementationPlan).count(),
        )
    assert before == after
    assert first == second


def test_v045_migration_revision_and_mac_lifecycle_are_current():
    root = Path(__file__).resolve().parents[1]
    migration = root / "migrations" / "versions" / "20260803_0029_v045_product_intelligence.py"
    assert migration.exists()
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision = "20260803_0028"' in source
    installer = root / "INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command"
    if installer.is_file():
        lifecycle = (root / "scripts" / "mac_lifecycle_common.sh").read_text(encoding="utf-8")
        assert 'CTH_RELEASE_VERSION="1.0.0"' in lifecycle
        assert 'CTH_RELEASE_SLUG="v1_0_0"' in lifecycle
        assert installer.stat().st_mode & 0o111
    else:
        assert (root / "install_windows.ps1").is_file()
