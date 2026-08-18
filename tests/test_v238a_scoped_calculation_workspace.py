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


def test_v238a_inventory_record_exposes_scoped_results() -> None:
    inventory_id, inventory_name, _ = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    link = soup.select_one(f'a[href="/inventarios/{inventory_id}/calculos"]')
    assert link is not None
    assert "Ver resultados" in link.get_text(" ", strip=True)
    assert inventory_name in response.text


def test_v238a_scoped_results_keep_explicit_inventory_and_are_read_only() -> None:
    inventory_id, inventory_name, period = _selected_inventory()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/calculos")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.select_one("#contenido-aplicacion")
    assert content is not None
    assert inventory_name in response.text
    assert period in response.text
    assert "Consulta explícita del periodo" in response.text
    assert "no cambia el periodo por defecto" in response.text

    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == f"/inventarios/{inventory_id}"

    assert content.select_one(f'form[action="/inventarios/{inventory_id}/recalcular"]') is None
    assert content.select_one('a[href="/informacion"]') is None
    assert content.select_one('a[href="/entrega-profesional"]') is None
    assert content.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None


def test_v238a_default_results_preserve_existing_operational_route() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/calculos")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert "Consulta explícita del periodo" not in response.text
    assert soup.select_one('a[href="/informacion"]') is not None
    assert soup.select_one('form[action^="/inventarios/"][action$="/recalcular"]') is not None


def test_v238a_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/calculos")

    assert response.status_code == 404
