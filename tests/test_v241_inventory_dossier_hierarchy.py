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


def _inventory_id() -> int:
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


def test_v241_inventory_header_keeps_only_local_actions() -> None:
    inventory_id = _inventory_id()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    head_actions = soup.select_one(".inventory-head .head-actions")
    assert head_actions is not None
    hrefs = {link.get("href") for link in head_actions.select("a[href]")}

    assert "/inventarios" in hrefs
    assert f"/inventarios/{inventory_id}/fuentes" in hrefs
    assert f"/inventarios/{inventory_id}/calculos" not in hrefs
    assert f"/inventarios/{inventory_id}/analisis" not in hrefs
    assert f"/inventarios/{inventory_id}/reduccion" not in hrefs
    assert f"/inventarios/{inventory_id}/reportes" not in hrefs
    assert f"/inventarios/{inventory_id}/entrega-profesional" not in hrefs


def test_v241_dossier_navigation_remains_complete_after_header_deduplication() -> None:
    inventory_id = _inventory_id()
    expected = [
        f"/inventarios/{inventory_id}",
        f"/inventarios/{inventory_id}/informacion",
        f"/inventarios/{inventory_id}/calculos",
        f"/inventarios/{inventory_id}/analisis",
        f"/inventarios/{inventory_id}/reduccion",
        f"/inventarios/{inventory_id}/reportes",
        f"/inventarios/{inventory_id}/entrega-profesional",
    ]

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    nav = soup.select_one("[data-inventory-dossier-nav]")
    assert nav is not None
    assert [link.get("href") for link in nav.select("a[href]")] == expected
    current = nav.select('a[aria-current="page"]')
    assert len(current) == 1
    assert current[0].get("href") == f"/inventarios/{inventory_id}"


def test_v241_inventory_context_copy_distinguishes_explicit_dossier_from_default_routes() -> None:
    inventory_id = _inventory_id()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    note = soup.select_one("[data-explicit-period-context]")
    assert note is not None
    text = note.get_text(" ", strip=True)
    assert "Expediente del periodo · contexto fijado por URL" in text
    assert "Las rutas generales de la aplicación continúan resolviendo el periodo más reciente por defecto" in text
    assert note.select_one('a[href="/inventarios"]') is not None
    assert note.select_one('a[href="/recorrido-inventario"]') is not None
    assert "vuelve primero al periodo por defecto" not in response.text.casefold()
