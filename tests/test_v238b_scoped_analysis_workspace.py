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


def test_v238b_inventory_and_results_expose_scoped_analysis() -> None:
    inventory_id, _, _ = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        inventory_page = client.get(f"/inventarios/{inventory_id}")
        results_page = client.get(f"/inventarios/{inventory_id}/calculos")

    assert inventory_page.status_code == 200
    assert results_page.status_code == 200
    inventory_soup = BeautifulSoup(inventory_page.text, "html.parser")
    results_soup = BeautifulSoup(results_page.text, "html.parser")
    assert inventory_soup.select_one(f'a[href="/inventarios/{inventory_id}/analisis"]') is not None
    assert results_soup.select_one(f'a[href="/inventarios/{inventory_id}/analisis"]') is not None


def test_v238b_scoped_analysis_keeps_period_and_hides_mutation_controls() -> None:
    inventory_id, inventory_name, period = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/analisis")

    assert response.status_code == 200
    assert inventory_name in response.text
    assert period in response.text
    assert "Consulta explícita del periodo" in response.text
    assert "no cambia el periodo por defecto" in response.text.lower()

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.select_one("#contenido-aplicacion")
    assert content is not None
    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == f"/inventarios/{inventory_id}"
    assert content.select_one('form[action="/analisis/indicadores/nuevo"]') is None
    assert content.select_one('a[href="/reduccion"]') is None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}/calculos"]') is not None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None


def test_v238b_default_analysis_preserves_operational_navigation() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/analisis")

    assert response.status_code == 200
    assert "Consulta explícita del periodo" not in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one('a[href="/reduccion"]') is not None


def test_v238b_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/analisis")

    assert response.status_code == 404
