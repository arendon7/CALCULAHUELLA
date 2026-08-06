from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.calculations import (
    ENGINE_VERSION,
    combine_relative_uncertainty,
    convert_value,
    normalize_factor_output,
    recalculate_source,
)
from app.database import (
    Base,
    EmissionCalculation,
    EmissionFactor,
    EmissionFactorVersion,
    EmissionSource,
    ENGINE,
    Inventory,
    SessionLocal,
    SourceFactorAssignment,
    UnitConversion,
    UnitDefinition,
    Gas,
    init_db,
)
from app.main import app
from conftest import restore_seed_database


def reset_database() -> None:
    restore_seed_database()


def test_output_mass_normalization_is_explicit() -> None:
    assert normalize_factor_output(2.5, "t CO2e", "CO2e")[0] == pytest.approx(2500)
    assert normalize_factor_output(2500, "g CH4", "CH4")[0] == pytest.approx(2.5)
    assert normalize_factor_output(2.5, "kg N2O", "N2O")[0] == pytest.approx(2.5)
    invalid, message = normalize_factor_output(2.5, "L", "CO2")
    assert invalid is None
    assert "no soportada" in message


def test_output_gas_mismatch_is_rejected() -> None:
    invalid, message = normalize_factor_output(1, "kg CH4", "N2O")
    assert invalid is None
    assert "no corresponde" in message


def test_uncertainty_warns_when_approach1_assumptions_need_review() -> None:
    combined, alerts = combine_relative_uncertainty(40, 10)
    assert combined == pytest.approx((40**2 + 10**2) ** 0.5)
    assert any("supera 30" in item for item in alerts)
    invalid, invalid_alerts = combine_relative_uncertainty(-1, 10)
    assert invalid is None
    assert invalid_alerts


def test_transitive_conversion_uses_bounded_graph() -> None:
    reset_database()
    with SessionLocal() as session:
        session.add(UnitDefinition(code="g", name="Gramo", dimension="mass", active=True))
        session.add(UnitConversion(from_unit="kg", to_unit="g", multiplier=1000, offset=0, active=True))
        session.commit()
        converted, note = convert_value(session, 1, "t", "g")
        assert converted == pytest.approx(1_000_000)
        assert "t → kg → g" in note


def test_ambiguous_gwp_configuration_does_not_default_to_ar6() -> None:
    reset_database()
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.id == 1))
        inventory.gwp_version = "Última versión disponible"
        source = session.scalar(select(EmissionSource).where(EmissionSource.name == "Diésel"))
        result = recalculate_source(session, source)
        rows = list(
            session.scalars(
                select(EmissionCalculation)
                .join(EmissionCalculation.activity_data)
                .where(EmissionCalculation.activity_data.has(source_id=source.id))
            )
        )
        assert result["calculations"] > 0
        assert rows and all(row.status == "Error" for row in rows)
        assert any("ambigua" in row.warning for row in rows)
        assert source.emissions == 0


def test_aggregated_co2e_and_per_gas_factors_cannot_be_mixed() -> None:
    reset_database()
    with SessionLocal() as session:
        source = session.scalar(select(EmissionSource).where(EmissionSource.name == "Electricidad"))
        per_gas = session.scalar(
            select(EmissionFactorVersion)
            .join(EmissionFactor)
            .where(EmissionFactor.name == "Diésel combustión fija · CO2 demo")
        )
        assert source is not None and per_gas is not None
        session.add(SourceFactorAssignment(source_id=source.id, factor_version_id=per_gas.id, active=True))
        session.flush()
        result = recalculate_source(session, source)
        rows = list(
            session.scalars(
                select(EmissionCalculation)
                .where(EmissionCalculation.activity_data.has(source_id=source.id))
            )
        )
        assert result["calculations"] > 0
        assert rows and all(row.status == "Error" for row in rows)
        assert all("mezclar" in row.warning for row in rows)
        assert source.emissions == 0


def test_existing_diesel_reference_result_is_preserved() -> None:
    reset_database()
    with SessionLocal() as session:
        source = session.scalar(select(EmissionSource).where(EmissionSource.name == "Diésel"))
        result = recalculate_source(session, source)
        session.commit()
        assert ENGINE_VERSION == "1.1.0"
        assert result["calculations"] == 36
        assert 40 < result["emissions"] < 42


def test_factor_governance_rejects_output_unit_for_a_different_gas() -> None:
    reset_database()
    with SessionLocal() as session:
        gas = session.scalar(select(Gas).where(Gas.code == "N2O"))
        gas_id = gas.id
    with TestClient(app) as client:
        login = client.post(
            "/login",
            data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        response = client.post(
            "/metodologia/factores/nuevo",
            data={
                "name": "Factor inválido de prueba",
                "activity_type": "Prueba",
                "gas_id": gas_id,
                "value": 1,
                "input_unit": "kg",
                "output_unit": "kg CH4",
                "version": "1.0",
                "source_organization": "Prueba",
                "publication_year": 2026,
                "uncertainty_percentage": 10,
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "no corresponde" in response.text
