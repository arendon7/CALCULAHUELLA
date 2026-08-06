from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import (
    ActivityFactorSelection,
    Base,
    CommercialLead,
    EmissionCalculation,
    EmissionFactorVersion,
    EmissionSource,
    ENGINE,
    SessionLocal,
    init_db,
)
from app.factor_advisor import advise_factor
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v049_public_landing_explains_value_greenatics_prices_and_flow():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Potenciado por" in response.text
        assert "GREENATICS" in response.text
        assert "Del propósito de la medición a una decisión de gestión" in response.text
        assert "Conversación técnica dato–factor" in response.text
        assert "PLANES Y PRECIOS DE REFERENCIA" in response.text
        assert "Dr. Carlos Andrés Uribe" in response.text
        assert "Mensajes y requerimientos" in response.text
        assert "$390.000" in response.text


def test_v049_public_contact_creates_traceable_commercial_request():
    with TestClient(app) as client:
        response = client.post(
            "/contacto",
            data={
                "company_name": "Empresa de prueba",
                "contact_name": "Ana Pérez",
                "email": "ana@example.com",
                "phone": "3000000000",
                "sector": "Servicios",
                "interest": "Gestión de Carbono",
                "message": "Necesitamos medir alcances 1, 2 y movilidad contratada antes de diciembre.",
                "accept_privacy": "yes",
                "accept_commercial": "no",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/?contacto=recibido#contacto"
    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).where(CommercialLead.email == "ana@example.com"))
        assert lead is not None
        assert lead.source == "Landing pública V1.0"
        assert lead.recommended_plan_code == "EMPRESARIAL"
        assert "movilidad contratada" in lead.notes
        assert "Autorización de privacidad: sí" in lead.notes


def test_v049_factor_advisor_and_record_specific_multi_factor_selection():
    with SessionLocal() as session:
        source = session.scalar(
            select(EmissionSource)
            .where(EmissionSource.activity_records.any())
            .options(selectinload(EmissionSource.activity_records))
        )
        assert source is not None
        record = source.activity_records[0]
        versions = list(
            session.scalars(
                select(EmissionFactorVersion).options(
                    selectinload(EmissionFactorVersion.factor),
                    selectinload(EmissionFactorVersion.gas),
                )
            )
        )
        candidates = [(advise_factor(session, source, record, version), version) for version in versions]
        calculable = [item for item in candidates if item[0]["calculable"] and not item[0].get("hard_blockers")]
        calculable.sort(key=lambda item: item[0]["score"], reverse=True)
        assert calculable
        first_advice, first_factor = calculable[0]
        assert first_advice["score"] >= 70
        second_factor = next(
            (version for advice, version in calculable[1:] if version.id != first_factor.id),
            None,
        )
        source_id, record_id = source.id, record.id

    with TestClient(app) as client:
        login(client)
        page = client.get(f"/fuentes/{source_id}")
        assert page.status_code == 200
        assert "CONVERSACIÓN TÉCNICA DATO–FACTOR" in page.text
        assert "Compara, justifica y aprueba los factores antes de afectar el cálculo" in page.text

        selected = client.post(
            f"/fuentes/{source_id}/datos/{record_id}/factores/seleccionar",
            data={
                "factor_version_id": first_factor.id,
                "rationale": "La unidad, geografía, actividad y periodo representan el dato reportado.",
            },
            follow_redirects=False,
        )
        assert selected.status_code == 303

        if second_factor is not None:
            selected_two = client.post(
                f"/fuentes/{source_id}/datos/{record_id}/factores/seleccionar",
                data={
                    "factor_version_id": second_factor.id,
                    "rationale": "Se requiere un segundo componente para desagregar gases del mismo dato.",
                },
                follow_redirects=False,
            )
            assert selected_two.status_code == 303

    with SessionLocal() as session:
        selections = list(
            session.scalars(
                select(ActivityFactorSelection).where(
                    ActivityFactorSelection.activity_data_id == record_id,
                    ActivityFactorSelection.active.is_(True),
                )
            )
        )
        assert len(selections) >= 1
        assert all(item.selection_status == "Propuesto" for item in selections)
        selection_ids = [item.id for item in selections]

    with TestClient(app) as client:
        login(client)
        for selection_id in selection_ids:
            reviewed = client.post(
                f"/fuentes/{source_id}/datos/{record_id}/factores/{selection_id}/revisar",
                data={"decision": "Aprobar", "review_notes": "Compatibilidad confirmada y sin doble conteo para el uso documentado."},
                follow_redirects=False,
            )
            assert reviewed.status_code == 303

    with SessionLocal() as session:
        selections = list(session.scalars(select(ActivityFactorSelection).where(
            ActivityFactorSelection.activity_data_id == record_id,
            ActivityFactorSelection.active.is_(True),
        )))
        selected_ids = {item.factor_version_id for item in selections if item.selection_status == "Aprobado"}
        calculations = list(session.scalars(select(EmissionCalculation).where(EmissionCalculation.activity_data_id == record_id)))
        assert {item.factor_version_id for item in calculations} == selected_ids
        assert all(item.compatibility_score > 0 and item.rationale and item.review_notes for item in selections)


def test_v049_windows_installers_and_dual_entry_are_present():
    current = Path(__file__).resolve().parents[1]
    root = current if (current / "1_INSTALAR_Y_ABRIR.bat").exists() else current.parent / "WINDOWS"
    required = [
        "1_INSTALAR_Y_ABRIR.bat",
        "2_ABRIR_CALCULA_TU_HUELLA.bat",
        "3_DETENER_CALCULA_TU_HUELLA.bat",
        "install_windows.ps1",
        "start_windows.ps1",
        "stop_windows.ps1",
        "WINDOWS.md",
    ]
    for name in required:
        assert (root / name).is_file(), name
    install = (root / "install_windows.ps1").read_text(encoding="utf-8")
    start = (root / "start_windows.ps1").read_text(encoding="utf-8")
    run = (root / "run.py").read_text(encoding="utf-8")
    assert "Python 3.11" in install
    assert "LOCALAPPDATA" in install
    assert "alembic upgrade head" in install
    assert "http://127.0.0.1:$Port/" in start
    assert 'url = f"http://{browser_host}:{port}/"' in run


def test_v049_version_and_migration_are_aligned():
    root = Path(__file__).resolve().parents[1]
    config = (root / "app/config.py").read_text(encoding="utf-8")
    migration = root / "migrations/versions/20260804_0030_v049_activity_factor_selection.py"
    assert 'version: str = "1.0.0"' in config
    assert migration.is_file()
    assert len(Base.metadata.tables) == 120
