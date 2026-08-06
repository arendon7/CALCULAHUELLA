from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.calculations import recalculate_source
from app.database import (
    ActivityData,
    Base,
    ENGINE,
    PeriodClose,
    PeriodCloseItem,
    PilotExecutionSourceLink,
    SessionLocal,
    init_db,
)
from app.main import app
from app.period_close import (
    assert_periods_editable,
    close_period,
    period_close_summary,
    reopen_period,
    submit_period_close,
)
from app.pilot_execution import start_pilot_execution


@pytest.fixture(autouse=True)
def fresh_database_v027():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def _login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def _prepare_single_ready_source(session):
    execution = start_pilot_execution(session, 1, "consultor@test", "Consultor prueba")
    session.commit()
    links = list(session.scalars(select(PilotExecutionSourceLink).where(PilotExecutionSourceLink.execution_id == execution.id)))
    keep = next(link for link in links if link.requirement.code == "YAR-ELEC")
    for link in links:
        if link.id != keep.id:
            session.delete(link)
    record = ActivityData(
        source_id=keep.source_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        value=1000,
        unit="kWh",
        data_origin="Factura",
        quality_level="A",
        notes="Evidencia: factura enero",
        status="Cargado",
        created_by="consultor@test",
    )
    session.add(record)
    session.flush()
    recalculate_source(session, keep.source)
    session.commit()
    return execution, keep, record


def test_v027_health_version():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["version"] == "1.0.0"


def test_v027_page_is_available_and_shows_blockers():
    with SessionLocal() as session:
        start_pilot_execution(session, 1, "consultor@test", "Consultor prueba")
        session.commit()
    with TestClient(app) as client:
        _login(client)
        page = client.get("/cierre-mensual?period=2026-01")
        assert page.status_code == 200
        assert "Cierre mensual del inventario" in page.text
        assert "Bloqueos" in page.text


def test_v027_empty_period_cannot_be_submitted():
    with SessionLocal() as session:
        start_pilot_execution(session, 1, "consultor@test", "Consultor prueba")
        session.commit()
        with pytest.raises(ValueError, match="No puede enviarse"):
            submit_period_close(session, 1, "2026-01", "consultor@test")


def test_v027_ready_period_can_be_submitted_closed_and_snapshotted():
    with SessionLocal() as session:
        execution, keep, _ = _prepare_single_ready_source(session)
        summary = period_close_summary(session, 1, "2026-01")
        assert summary["blockers"] == []
        assert summary["metrics"]["data_coverage"] == 100
        submitted = submit_period_close(session, 1, "2026-01", "consultor@test", "Datos conciliados")
        session.commit()
        assert submitted.status == "En revisión"
        closed = close_period(session, 1, "2026-01", "revisor@test", "Revisión conforme")
        session.commit()
        assert closed.status == "Cerrado"
        assert len(closed.snapshot_hash) == 64
        assert session.scalar(select(PeriodCloseItem).where(PeriodCloseItem.period_close_id == closed.id)) is not None
        with pytest.raises(ValueError, match="está cerrado"):
            assert_periods_editable(session, execution.inventory_id, [(date(2026, 1, 1), date(2026, 1, 31))])


def test_v027_reopen_requires_reason_and_preserves_previous_hash():
    with SessionLocal() as session:
        _prepare_single_ready_source(session)
        submit_period_close(session, 1, "2026-01", "consultor@test")
        session.commit()
        closed = close_period(session, 1, "2026-01", "revisor@test")
        session.commit()
        old_hash = closed.snapshot_hash
        with pytest.raises(ValueError, match="al menos 10"):
            reopen_period(session, 1, "2026-01", "admin@test", "corto")
        reopened = reopen_period(session, 1, "2026-01", "admin@test", "Corrección documentada de factura")
        session.commit()
        assert reopened.status == "Reabierto"
        assert reopened.snapshot_hash == old_hash
        assert reopened.reopen_reason.startswith("Corrección")


def test_v027_client_can_view_but_cannot_close():
    with SessionLocal() as session:
        start_pilot_execution(session, 1, "consultor@test", "Consultor prueba")
        session.commit()
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/cierre-mensual?period=2026-01")
        assert page.status_code == 200
        denied = client.post("/cierre-mensual/cerrar", data={"period": "2026-01"})
        assert denied.status_code == 403


def test_v027_closed_period_rejects_direct_activity_edit():
    with SessionLocal() as session:
        _, _, record = _prepare_single_ready_source(session)
        record_id = record.id
        submit_period_close(session, 1, "2026-01", "consultor@test")
        session.commit()
        close_period(session, 1, "2026-01", "revisor@test")
        session.commit()
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        response = client.post(
            f"/informacion/datos/{record_id}/editar",
            data={
                "value": 1200,
                "unit": "kWh",
                "data_origin": "Factura",
                "status": "Cargado",
                "notes": "Intento posterior al cierre",
            },
        )
        assert response.status_code == 409
