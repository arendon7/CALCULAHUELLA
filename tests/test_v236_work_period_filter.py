from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal, WorkItem
from app.main import app


CURRENT_MARKER = "V2.36 · tarea periodo por defecto"
HISTORICAL_MARKER = "V2.36 · tarea periodo histórico"
TRANSVERSAL_MARKER = "V2.36 · tarea transversal"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _new_item(organization_id: int, inventory_id: int | None, title: str, created_by: str) -> WorkItem:
    return WorkItem(
        organization_id=organization_id,
        inventory_id=inventory_id,
        stage_code="collect",
        work_type="data_request",
        title=title,
        status_code="assigned",
        priority="normal",
        requester_email=created_by,
        acceptance_criteria="La tarea aparece únicamente en el filtro de periodo correspondiente.",
        next_action="Revisar el contexto antes de actuar.",
        created_by=created_by,
    )


def test_v236_work_queue_filters_default_historical_and_transversal_tasks() -> None:
    item_ids: list[int] = []
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventories = list(
            session.scalars(
                select(Inventory)
                .where(Inventory.organization_id == user.organization_id)
                .order_by(Inventory.start_date.desc(), Inventory.id.desc())
            )
        )
        assert len(inventories) >= 2
        current, historical = inventories[0], inventories[-1]
        items = [
            _new_item(user.organization_id, current.id, CURRENT_MARKER, user.email),
            _new_item(user.organization_id, historical.id, HISTORICAL_MARKER, user.email),
            _new_item(user.organization_id, None, TRANSVERSAL_MARKER, user.email),
        ]
        session.add_all(items)
        session.commit()
        item_ids = [item.id for item in items]
        current_id = current.id
        historical_id = historical.id

    try:
        with TestClient(app) as client:
            login(client)
            historical_response = client.get(f"/mi-trabajo?scope=all&inventory_id={historical_id}")
            transversal_response = client.get("/mi-trabajo?scope=all&inventory_id=transversal")
            api_response = client.get(f"/api/mi-trabajo?scope=all&inventory_id={historical_id}")

        assert historical_response.status_code == 200
        assert HISTORICAL_MARKER in historical_response.text
        assert CURRENT_MARKER not in historical_response.text
        assert TRANSVERSAL_MARKER not in historical_response.text
        historical_soup = BeautifulSoup(historical_response.text, "html.parser")
        selector = historical_soup.select_one("[data-work-period-filter]")
        assert selector is not None
        selected = selector.select_one("option[selected]")
        assert selected is not None
        assert selected.get("value") == str(historical_id)
        assert "histórico" in selected.get_text(" ", strip=True)

        assert transversal_response.status_code == 200
        assert TRANSVERSAL_MARKER in transversal_response.text
        assert CURRENT_MARKER not in transversal_response.text
        assert HISTORICAL_MARKER not in transversal_response.text

        assert api_response.status_code == 200
        payload = api_response.json()
        assert payload["inventory_filter"] == str(historical_id)
        assert all(item["inventory_id"] == historical_id for item in payload["items"])
        assert all(item["inventory_id"] != current_id for item in payload["items"])
    finally:
        if item_ids:
            with SessionLocal() as session:
                for item_id in item_ids:
                    item = session.get(WorkItem, item_id)
                    if item is not None:
                        session.delete(item)
                session.commit()
