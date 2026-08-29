from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    AppUser,
    DataImportBatch,
    Inventory,
    PilotExecution,
    PilotProject,
    SessionLocal,
    SupportTicket,
)
from app.main import app


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v235_legacy_ticket_query_resolves_to_real_detail_and_keeps_period_context() -> None:
    ticket_id: int | None = None
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        assert inventory is not None
        ticket = SupportTicket(
            organization_id=user.organization_id,
            inventory_id=inventory.id,
            public_reference="V235-TEMP",
            created_by=user.email,
            subject="V2.35 · validar contexto de soporte",
            description="Caso temporal para comprobar el enlace específico y el periodo mostrado.",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id
        inventory_id = inventory.id

    try:
        with TestClient(app) as client:
            login(client)
            alias = client.get(f"/soporte?ticket_id={ticket_id}", follow_redirects=False)
            assert alias.status_code == 303
            assert alias.headers["location"] == f"/soporte/{ticket_id}"
            detail = client.get(alias.headers["location"])

        assert detail.status_code == 200
        soup = BeautifulSoup(detail.text, "html.parser")
        pill = soup.select_one(".topbar .version-pill")
        assert pill is not None
        assert pill.get("href") == f"/inventarios/{inventory_id}"
        assert "Periodo mostrado" in pill.get_text(" ", strip=True)
    finally:
        if ticket_id is not None:
            with SessionLocal() as session:
                persisted = session.get(SupportTicket, ticket_id)
                if persisted is not None:
                    session.delete(persisted)
                    session.commit()


def test_v235_selected_quality_batch_keeps_global_shell_neutral_and_labels_local_period() -> None:
    batch_id: int | None = None
    created_execution_id: int | None = None
    created_pilot_id: int | None = None
    reused_execution_id: int | None = None
    restore_unbound_execution = False
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        assert inventory is not None

        pilot = session.scalar(
            select(PilotProject).where(
                PilotProject.organization_id == user.organization_id,
                PilotProject.code == "GREENATICS-2026",
            )
        )
        if pilot is None:
            pilot = PilotProject(
                organization_id=user.organization_id,
                code="GREENATICS-2026",
                name="V2.35 · piloto temporal de contexto",
                reporting_year=inventory.start_date.year,
            )
            session.add(pilot)
            session.flush()
            created_pilot_id = pilot.id

        execution = session.scalar(select(PilotExecution).where(PilotExecution.pilot_id == pilot.id))
        if execution is None:
            execution = PilotExecution(
                pilot_id=pilot.id,
                inventory_id=inventory.id,
                status="En ejecución",
                started_by=user.email,
            )
            session.add(execution)
            session.flush()
            created_execution_id = execution.id
        else:
            reused_execution_id = execution.id
            if execution.inventory_id is not None:
                execution_inventory = session.get(Inventory, execution.inventory_id)
                assert execution_inventory is not None
                assert execution_inventory.organization_id == user.organization_id
                inventory = execution_inventory
            else:
                restore_unbound_execution = True
                execution.inventory_id = inventory.id
                session.flush()

        batch = DataImportBatch(
            organization_id=user.organization_id,
            execution_id=execution.id,
            inventory_id=inventory.id,
            code="V235-QUALITY-CONTEXT",
            filename="v235-quality-context.xlsx",
            file_hash="2" * 64,
            status="Validado",
            total_rows=1,
            valid_rows=1,
            quality_score=100,
            uploaded_by=user.email,
        )
        session.add(batch)
        session.commit()
        batch_id = batch.id
        inventory_id = inventory.id
        batch_code = batch.code
        inventory_name = inventory.name
        period_range = f"{inventory.start_date.strftime('%d/%m/%Y')} – {inventory.end_date.strftime('%d/%m/%Y')}"

    try:
        with TestClient(app) as client:
            login(client)
            response = client.get(f"/calidad-datos?batch_id={batch_id}")

        assert response.status_code == 200
        assert batch_code in response.text
        soup = BeautifulSoup(response.text, "html.parser")
        pill = soup.select_one(".topbar .version-pill")
        assert pill is not None
        assert pill.get("href") == "/inventario"
        assert "Ver por defecto" in pill.get_text(" ", strip=True)
        context = soup.select_one("[data-selected-batch-context]")
        assert context is not None
        context_text = context.get_text(" ", strip=True)
        assert inventory_name in context_text
        assert period_range in context_text
        assert "los KPI superiores resumen el centro de calidad" in context_text
        assert context.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None
    finally:
        with SessionLocal() as session:
            if batch_id is not None:
                persisted = session.get(DataImportBatch, batch_id)
                if persisted is not None:
                    session.delete(persisted)
                    session.flush()
            if created_execution_id is not None:
                created_execution = session.get(PilotExecution, created_execution_id)
                if created_execution is not None:
                    session.delete(created_execution)
                    session.flush()
            elif reused_execution_id is not None and restore_unbound_execution:
                reused_execution = session.get(PilotExecution, reused_execution_id)
                if reused_execution is not None:
                    reused_execution.inventory_id = None
                    session.flush()
            if created_pilot_id is not None:
                created_pilot = session.get(PilotProject, created_pilot_id)
                if created_pilot is not None:
                    session.delete(created_pilot)
            session.commit()
