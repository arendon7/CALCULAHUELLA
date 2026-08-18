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


def _oldest_inventory_id() -> int:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.asc(), Inventory.id.asc())
        )
        assert inventory is not None
        return inventory.id


def _sidebar_links(soup: BeautifulSoup) -> list:
    return list(soup.select("#navegacion-principal a.nav-item[href]"))


def test_v242_scoped_results_keep_period_in_global_sidebar() -> None:
    inventory_id = _oldest_inventory_id()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/calculos")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    sidebar = _sidebar_links(soup)
    preserving = [link for link in sidebar if link.get("data-period-preserving") == "true"]
    hrefs = {link.get("href") for link in preserving}

    assert f"/inventarios/{inventory_id}/informacion" in hrefs
    assert f"/inventarios/{inventory_id}/calculos" in hrefs
    assert f"/inventarios/{inventory_id}/entrega-profesional" in hrefs
    assert f"/inventarios/{inventory_id}/reduccion" in hrefs
    assert "/informacion" not in {link.get("href") for link in sidebar}
    assert "/calculos" not in {link.get("href") for link in sidebar}

    current = soup.select_one('#navegacion-principal a.nav-item[aria-current="page"]')
    assert current is not None
    assert current.get("href") == f"/inventarios/{inventory_id}/calculos"
    assert "mantener periodo mostrado" in (current.get("aria-label") or "")


def test_v242_scoped_information_keeps_period_in_mobile_taskbar_when_present() -> None:
    inventory_id = _oldest_inventory_id()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/informacion")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    mobile = soup.select_one("nav.mobile-taskbar")
    if mobile is None:
        # Complete mode intentionally hides the compact taskbar; desktop is still authoritative.
        return

    information = mobile.select_one(f'a[href="/inventarios/{inventory_id}/informacion"]')
    assert information is not None
    assert information.get("data-period-preserving") == "true"
    assert mobile.select_one('a[href="/informacion"]') is None


def test_v242_generic_results_keep_latest_default_navigation_contract() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/calculos")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    sidebar = _sidebar_links(soup)
    hrefs = {link.get("href") for link in sidebar}

    assert "/calculos" in hrefs
    assert "/informacion" in hrefs
    assert not soup.select("#navegacion-principal a[data-period-preserving]")
    current = soup.select_one('#navegacion-principal a.nav-item[aria-current="page"]')
    assert current is not None
    assert current.get("href") == "/calculos"


def test_v242_dossier_bar_still_owns_all_seven_period_views() -> None:
    inventory_id = _oldest_inventory_id()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/analisis")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    dossier = soup.select_one("[data-inventory-dossier-nav]")
    assert dossier is not None
    assert [link.get("href") for link in dossier.select("a[href]")] == [
        f"/inventarios/{inventory_id}",
        f"/inventarios/{inventory_id}/informacion",
        f"/inventarios/{inventory_id}/calculos",
        f"/inventarios/{inventory_id}/analisis",
        f"/inventarios/{inventory_id}/reduccion",
        f"/inventarios/{inventory_id}/reportes",
        f"/inventarios/{inventory_id}/entrega-profesional",
    ]
