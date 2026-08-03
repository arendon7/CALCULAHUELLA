import math

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.colombia_library import (
    calculate_biogas_balance,
    calculate_combustion,
    calculate_fertilizer,
    calculate_wastewater,
    colombia_library_summary,
)
from app.database import (
    Base,
    ENGINE,
    EmissionFactor,
    FactorDocumentation,
    MethodologySourceDocument,
    MethodologyValidationRun,
    SessionLocal,
    init_db,
)
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_v028():
    Base.metadata.drop_all(ENGINE)
    init_db()
    yield


def _login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def test_v028_health_and_page():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "0.45.5"
        _login(client)
        page = client.get("/metodologia/colombia")
        assert page.status_code == 200
        assert "Biblioteca metodológica para Colombia" in page.text
        assert "Balance operativo" in page.text


def test_v028_seeds_controlled_sources_factors_and_reference_suite():
    with SessionLocal() as session:
        summary = colombia_library_summary(session)
        assert summary["counts"]["documents"] >= 7
        assert summary["counts"]["factors"] >= 13
        assert summary["counts"]["reference_cases"] == 8
        assert session.scalar(select(MethodologySourceDocument).where(MethodologySourceDocument.code == "COL-DECRETO-926-2017"))
        fecoc = session.scalar(select(MethodologySourceDocument).where(MethodologySourceDocument.code == "EAAB-FECOC-2016"))
        assert fecoc and "revisión" in fecoc.status.lower()
        factor = session.scalar(select(EmissionFactor).where(EmissionFactor.name == "Diésel B10 Colombia · CO2 FECOC transcrito"))
        assert factor and factor.is_demo is False
        documentation = session.scalar(select(FactorDocumentation).join_from(FactorDocumentation, factor.versions[0].__class__).where(FactorDocumentation.factor_version_id == factor.versions[0].id))
        assert documentation.reporting_use == "Piloto"
        run = session.scalar(select(MethodologyValidationRun).order_by(MethodologyValidationRun.id.desc()))
        assert run.engine_version == "0.45.0"
        assert run.total_cases >= 20
        assert run.failed_cases == 0


def test_v028_combustion_converts_litres_to_gallons():
    result = calculate_combustion("REG-ACPM", 37.85411784, "L")
    assert math.isclose(result["normalized_value"], 10.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(result["co2e_kg"], 101.33, rel_tol=0, abs_tol=1e-9)
    assert result["reporting_use"] == "Piloto condicionado"


def test_v028_wastewater_uses_bo_mcf_and_recovery():
    result = calculate_wastewater(1000, "COD", 0.8, 20)
    assert result["gross_ch4_kg"] == 200
    assert result["emitted_ch4_kg"] == 180
    assert result["co2e_kg"] == 4860


def test_v028_fertilizer_separates_direct_and_indirect_emissions():
    result = calculate_fertilizer(1000, "wet", "urea", True, True)
    assert math.isclose(result["direct_n2o_kg"], 25.142857142857142, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(result["volatilization_n2o_kg"], 3.3, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(result["leaching_n2o_kg"], 4.148571428571429, rel_tol=0, abs_tol=1e-9)
    assert result["co2e_kg"] > 8000


def test_v028_biogas_balance_exposes_unassigned_volume_and_fugitive_ch4():
    result = calculate_biogas_balance(1000, 800, 100, 50, 0.6, 2)
    assert result["unassigned_m3"] == 50
    assert result["balanced"] is False
    assert math.isclose(result["emitted_ch4_kg"], 70 * 0.6 * 0.7168, rel_tol=0, abs_tol=1e-9)


def test_v028_export_and_api():
    with TestClient(app) as client:
        _login(client)
        api = client.get("/api/metodologia/colombia")
        assert api.status_code == 200
        assert api.json()["version"] == "0.28.0"
        export = client.get("/metodologia/colombia/exportar.xlsx")
        assert export.status_code == 200
        assert export.content.startswith(b"PK")


def test_v028_form_calculator_is_csrf_protected_and_works_with_browser_token():
    with TestClient(app) as client:
        _login(client)
        client.get("/metodologia/colombia")
        response = client.post("/metodologia/colombia/calcular-combustion", data={"factor_code": "REG-GN", "amount": "100", "amount_unit": "m3"})
        assert response.status_code == 200
        assert "0.195 tCO₂e" in response.text
