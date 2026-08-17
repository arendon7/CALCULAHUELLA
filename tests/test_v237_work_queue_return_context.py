from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal, WorkItem
from app.main import app
from app.workflow_web import _work_queue_url


MARKER = "V2.37 · conservar contexto de bandeja"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v237_return_builder_only_accepts_known_filters_not_arbitrary_urls() -> None:
    assert _work_queue_url(
        status="javascript:alert(1)",
        stage="../../control",
        scope="https://example.com",
        inventory_id="not-an-id",
        work_item_id=7,
    ) == "/mi-trabajo#tarea-7"
    assert _work_queue_url(
        stage="collect",
        scope="all",
        inventory_id="transversal",
    ) == "/mi-trabajo?stage=collect&scope=all&inventory_id=transversal"


def test_v237_action_and_sync_forms_preserve_the_current_period_filter() -> None:
    item_id: int | None = None
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.asc(), Inventory.id.asc())
        )
        assert inventory is not None
        item = WorkItem(
            organization_id=user.organization_id,
            inventory_id=inventory.id,
            stage_code="collect",
            work_type="data_request",
            title=MARKER,
            status_code="assigned",
            priority="normal",
            requester_email=user.email,
            assignee_role="Consultor",
            acceptance_criteria="Conservar los filtros de la bandeja después de la acción.",
            next_action="Revisar el retorno.",
            created_by=user.email,
        )
        session.add(item)
        session.commit()
        item_id = item.id
        item_version = item.version
        inventory_id = inventory.id

    try:
        with TestClient(app) as client:
            login(client)
            page = client.get(f"/mi-trabajo?stage=collect&scope=all&inventory_id={inventory_id}")
            assert page.status_code == 200
            soup = BeautifulSoup(page.text, "html.parser")
            card = soup.select_one(f"#tarea-{item_id}")
            assert card is not None
            action_form = card.select_one("form.work-action-form")
            assert action_form is not None
            assert action_form.select_one('input[name="return_stage"]')["value"] == "collect"
            assert action_form.select_one('input[name="return_scope"]')["value"] == "all"
            assert action_form.select_one('input[name="return_inventory_id"]')["value"] == str(inventory_id)
            sync_form = soup.select_one('form[action="/mi-trabajo/sincronizar"]')
            assert sync_form is not None
            assert sync_form.select_one('input[name="return_inventory_id"]')["value"] == str(inventory_id)

            result = client.post(
                f"/mi-trabajo/{item_id}/accion",
                data={
                    "action": "accion-invalida",
                    "comment": "Prueba de retorno seguro",
                    "expected_version": str(item_version),
                    "return_stage": "collect",
                    "return_scope": "all",
                    "return_inventory_id": str(inventory_id),
                },
                follow_redirects=False,
            )

        assert result.status_code == 303
        assert result.headers["location"] == (
            f"/mi-trabajo?stage=collect&scope=all&inventory_id={inventory_id}#tarea-{item_id}"
        )
    finally:
        if item_id is not None:
            with SessionLocal() as session:
                item = session.get(WorkItem, item_id)
                if item is not None:
                    session.delete(item)
                    session.commit()
