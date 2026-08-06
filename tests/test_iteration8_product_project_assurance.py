from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    AssuranceEngagement, Base, ENGINE, MitigationProject, ProductFootprintStudy,
    SessionLocal, init_db,
)
from app.main import app
from app.product_project_assurance import (
    assurance_readiness, calculate_product_stage, calculate_project_reduction,
    product_summary, project_readiness,
)


@pytest.fixture(autouse=True)
def fresh_database_iteration8():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def test_product_stage_normalizes_units_and_separates_accounting_types():
    assert calculate_product_stage(1000, 2.5, "kg CO2e") == 2.5
    assert calculate_product_stage(1000, 2500, "g CO2e") == 2.5
    assert calculate_product_stage(2, 1.25, "t CO2e") == 2.5
    with pytest.raises(ValueError):
        calculate_product_stage(1, 1, "kg CH4")


def test_project_reduction_formula_includes_leakage_and_removals():
    assert calculate_project_reduction(100, 62, 4, 3) == 37
    with pytest.raises(ValueError):
        calculate_project_reduction(100, -1, 0, 0)


def test_product_page_create_stage_api_and_approval():
    with TestClient(app) as client:
        login(client)
        assert client.get("/huella-producto").status_code == 200
        created = client.post("/huella-producto/nueva", data={
            "product_name": "Fertilizante organomineral", "product_code": "WG-01",
            "declared_unit": "1 t de producto", "reference_flow": "1",
            "boundary": "De la cuna a la puerta", "methodology": "ISO 14067:2018",
            "pcr_reference": "PCR fertilizantes 2025", "allocation_method": "Masa",
            "cutoff_rule_percent": "1", "biogenic_treatment": "Reporte separado",
            "land_use_included": "on", "data_quality_rating": "B",
        }, follow_redirects=False)
        assert created.status_code == 303
    with SessionLocal() as session:
        study = session.scalar(select(ProductFootprintStudy).where(ProductFootprintStudy.product_code == "WG-01"))
        study_id = study.id
    with TestClient(app) as client:
        login(client)
        for code, activity, value, factor in (
            ("A1", "Materias primas", "1000", "0.45"),
            ("A3", "Producción", "850", "0.22"),
        ):
            response = client.post(f"/huella-producto/{study_id}/etapas", data={
                "stage_code": code, "accounting_type": "Emisión", "activity_name": activity,
                "activity_value": value, "activity_unit": "kg", "factor_value": factor,
                "factor_output_unit": "kg CO2e", "data_source": "Factura y factor aprobado",
                "geography": "Colombia", "reference_year": "2025", "uncertainty_percentage": "8",
                "evidence_reference": "EXP-001",
            }, follow_redirects=False)
            assert response.status_code == 303
        api = client.get("/api/huella-producto")
        assert api.status_code == 200
        summary = api.json()["studies"][0]["summary"]
        assert round(summary["gross_emissions"], 6) == 0.637
        reviewed = client.post(f"/huella-producto/{study_id}/revisar", data={"status": "Aprobado"}, follow_redirects=False)
        assert reviewed.status_code == 303
    with SessionLocal() as session:
        study = session.scalar(select(ProductFootprintStudy).where(ProductFootprintStudy.id == study_id))
        assert study.status == "Aprobado"


def test_project_workflow_does_not_touch_inventory_and_requires_governance():
    with TestClient(app) as client:
        login(client)
        response = client.post("/proyectos-mitigacion/nuevo", data={
            "name": "Captura de biogás", "project_type": "Residuos y circularidad",
            "methodology": "ISO 14064-2:2019", "baseline_scenario": "Liberación de metano sin captura",
            "project_scenario": "Captura y aprovechamiento energético", "additionality_basis": "Inversión no obligatoria y barrera financiera",
            "monitoring_plan": "Medición mensual de caudal, metano y destrucción", "leakage_sources": "Consumo auxiliar",
            "ownership_statement": "Greenatics conserva la titularidad", "double_counting_control": "Registro único y sin venta de créditos",
            "start_date": "2026-01-01", "end_date": "2030-12-31", "estimated_baseline_tco2e": "1000",
            "estimated_project_tco2e": "120", "estimated_leakage_tco2e": "20", "estimated_removals_tco2e": "0",
        }, follow_redirects=False)
        assert response.status_code == 303
    with SessionLocal() as session:
        project = session.scalar(select(MitigationProject).where(MitigationProject.name == "Captura de biogás"))
        assert project.estimated_reduction_tco2e == 860
        assert project_readiness(project) == []
        project_id = project.id
    with TestClient(app) as client:
        login(client)
        response = client.post(f"/proyectos-mitigacion/{project_id}/monitoreo", data={
            "period_start": "2026-01-01", "period_end": "2026-12-31", "baseline_tco2e": "200",
            "project_tco2e": "35", "leakage_tco2e": "5", "removals_tco2e": "0",
            "uncertainty_percentage": "12", "evidence_reference": "MRV-2026",
        }, follow_redirects=False)
        assert response.status_code == 303
        api = client.get("/api/proyectos-mitigacion")
        assert api.status_code == 200
        assert api.json()["projects"][0]["summary"]["estimated_reduction"] == 860


def test_assurance_statement_requires_independence_and_no_material_open_findings():
    with TestClient(app) as client:
        login(client, "verificador@calculatuhuella.local")
        assert client.get("/aseguramiento").status_code == 200
        created = client.post("/aseguramiento/nuevo", data={
            "subject_type": "Inventario corporativo", "subject_reference": "Inventario 2025",
            "engagement_type": "Verificación", "standard": "ISO 14064-3:2019", "assurance_level": "Limitado",
            "materiality_percent": "5", "criteria": "GHG Protocol Corporate Standard e ISO 14064-1",
            "scope": "Alcances 1, 2 y categorías materiales de Alcance 3", "verifier_organization": "Verifica Carbono S.A.S.",
            "lead_verifier": "Laura Verificadora", "independence_declaration": "Sin relaciones financieras ni de consultoría con la organización",
            "competence_basis": "Equipo competente en GEI, energía, residuos y aseguramiento", "start_date": "2026-08-01", "end_date": "2026-08-31",
        }, follow_redirects=False)
        assert created.status_code == 303
    with SessionLocal() as session:
        engagement = session.scalar(select(AssuranceEngagement).where(AssuranceEngagement.subject_reference == "Inventario 2025"))
        assert assurance_readiness(engagement) == []
        engagement_id = engagement.id
    with TestClient(app) as client:
        login(client, "verificador@calculatuhuella.local")
        issued = client.post(f"/aseguramiento/{engagement_id}/emitir", data={
            "opinion": "Sin salvedades", "conclusion": "La declaración de GEI está presentada razonablemente conforme a los criterios.",
            "statement_date": "2026-08-31",
        }, follow_redirects=False)
        assert issued.status_code == 303
        api = client.get("/api/aseguramiento")
        assert api.status_code == 200
        assert api.json()["summary"]["issued"] == 1
    with SessionLocal() as session:
        engagement = session.get(AssuranceEngagement, engagement_id)
        assert engagement.status == "Declaración emitida"
        assert engagement.opinion == "Sin salvedades"


def test_navigation_uses_single_assurance_entry_and_keeps_historical_desk_linked():
    with TestClient(app) as client:
        login(client, "revisor@calculatuhuella.local")
        page = client.get("/aseguramiento")
        assert page.status_code == 200
        assert "Abrir mesa histórica de hallazgos" in page.text
        dashboard = client.get("/dashboard")
        assert "Aseguramiento independiente" not in dashboard.text
        switched = client.post(
            "/preferencias/vista",
            data={"mode": "complete", "return_url": "/dashboard"},
            follow_redirects=False,
        )
        assert switched.status_code == 303
        complete_dashboard = client.get("/dashboard")
        assert "Aseguramiento independiente" in complete_dashboard.text
        assert "Portal del verificador" not in complete_dashboard.text
