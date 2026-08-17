from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, DataImportBatch, Inventory, SessionLocal, SupportTicket
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
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        batch = session.scalar(
            select(DataImportBatch)
            .where(
                DataImportBatch.organization_id == user.organization_id,
                DataImportBatch.inventory_id.is_not(None),
            )
            .order_by(DataImportBatch.id.desc())
        )
        assert batch is not None
        batch_id = batch.id
        inventory_id = batch.inventory_id
        batch_code = batch.code
        inventory = session.get(Inventory, inventory_id)
        assert inventory is not None
        inventory_name = inventory.name
        period_range = f"{inventory.start_date.strftime('%d/%m/%Y')} – {inventory.end_date.strftime('%d/%m/%Y')}"

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
