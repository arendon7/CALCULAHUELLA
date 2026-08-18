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


def _selected_inventory() -> tuple[int, str, str]:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.asc(), Inventory.id.asc())
        )
        assert inventory is not None
        period = f"{inventory.start_date.strftime('%d/%m/%Y')} – {inventory.end_date.strftime('%d/%m/%Y')}"
        return inventory.id, inventory.name, period


def test_v238c_inventory_and_analysis_expose_scoped_reduction() -> None:
    inventory_id, _, _ = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        inventory_page = client.get(f"/inventarios/{inventory_id}")
        analysis_page = client.get(f"/inventarios/{inventory_id}/analisis")

    assert inventory_page.status_code == 200
    assert analysis_page.status_code == 200
    inventory_soup = BeautifulSoup(inventory_page.text, "html.parser")
    analysis_soup = BeautifulSoup(analysis_page.text, "html.parser")
    assert inventory_soup.select_one(f'a[href="/inventarios/{inventory_id}/reduccion"]') is not None
    assert analysis_soup.select_one(f'a[href="/inventarios/{inventory_id}/reduccion"]') is not None


def test_v238c_scoped_reduction_keeps_period_and_has_no_mutation_controls() -> None:
    inventory_id, inventory_name, period = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/reduccion")

    assert response.status_code == 200
    assert inventory_name in response.text
    assert period in response.text
    assert "Consulta explícita del periodo" in response.text
    assert "sin cambiar el contexto por defecto" in response.text

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.select_one("#contenido-aplicacion")
    assert content is not None
    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == f"/inventarios/{inventory_id}"
    assert not content.select('form[method="post"]')
    assert content.select_one('a[href="/escenarios"]') is None
    assert content.select_one('a[href="/reduccion/exportar.xlsx"]') is None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}/analisis"]') is not None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}/calculos"]') is not None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None


def test_v238c_default_reduction_preserves_operational_tools() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/reduccion")

    assert response.status_code == 200
    assert "Consulta explícita del periodo" not in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one('a[href="/escenarios"]') is not None
    assert soup.select_one('a[href="/reduccion/exportar.xlsx"]') is not None


def test_v238c_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/reduccion")

    assert response.status_code == 404
