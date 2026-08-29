from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal
from app.main import app


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v230_explicit_period_topbar_stays_on_displayed_inventory() -> None:
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
        explicit_inventory = inventories[-1]

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{explicit_inventory.id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == f"/inventarios/{explicit_inventory.id}"
    assert "Periodo mostrado" in pill.get_text(" ", strip=True)
    assert str(explicit_inventory.base_year) in pill.get_text(" ", strip=True)
    assert pill.get("href") != "/entrega-profesional"


def test_v230_pages_without_explicit_inventory_offer_default_period_without_inventing_selection() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == "/inventario"
    assert "Ver por defecto" in pill.get_text(" ", strip=True)
    assert "periodo activos" not in response.text.lower()
