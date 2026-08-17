from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal, WorkItem
from app.main import app


MARKER = "V2.31 · tarea con periodo explícito"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v231_work_card_shows_the_inventory_period_it_belongs_to() -> None:
    item_id: int | None = None
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        inventories = list(
            session.scalars(
                select(Inventory)
                .where(Inventory.organization_id == db_user.organization_id)
                .order_by(Inventory.start_date.desc(), Inventory.id.desc())
            )
        )
        assert inventories
        inventory = inventories[-1]
        item = WorkItem(
            organization_id=db_user.organization_id,
            inventory_id=inventory.id,
            stage_code="collect",
            work_type="data_request",
            title=MARKER,
            status_code="assigned",
            priority="normal",
            requester_user_id=db_user.id,
            requester_email=db_user.email,
            acceptance_criteria="La tarea conserva el periodo explícito en la bandeja.",
            next_action="Revisar el periodo antes de actuar.",
            created_by=db_user.email,
        )
        session.add(item)
        session.commit()
        item_id = item.id
        inventory_id = inventory.id
        inventory_name = inventory.name
        expected_range = f"{inventory.start_date.strftime('%d/%m/%Y')}–{inventory.end_date.strftime('%d/%m/%Y')}"

    try:
        with TestClient(app) as client:
            login(client)
            response = client.get("/mi-trabajo?scope=all")

        assert response.status_code == 200
        soup = BeautifulSoup(response.text, "html.parser")
        card = soup.select_one(f"#tarea-{item_id}")
        assert card is not None
        assert card.get("data-work-inventory-id") == str(inventory_id)
        context = card.select_one(".work-period-context")
        assert context is not None
        assert inventory_name in context.get_text(" ", strip=True)
        assert expected_range in context.get_text(" ", strip=True)
        assert card.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None
    finally:
        if item_id is not None:
            with SessionLocal() as session:
                persisted = session.get(WorkItem, item_id)
                if persisted is not None:
                    session.delete(persisted)
                    session.commit()


def test_v231_work_creation_selector_labels_default_historical_and_transversal_contexts() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/mi-trabajo?scope=all")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    selector = soup.select_one('select[name="inventory_id"]')
    assert selector is not None
    labels = [option.get_text(" ", strip=True) for option in selector.select("option")]
    assert labels[0] == "Trabajo transversal · sin periodo específico"
    assert any("por defecto" in label for label in labels[1:])
    assert any("histórico" in label for label in labels[1:])
