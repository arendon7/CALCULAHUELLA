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


def test_v238d2_inventory_record_exposes_scoped_delivery() -> None:
    inventory_id, _, _ = _selected_inventory()
    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}/entrega-profesional"]') is not None


def test_v238d2_scoped_delivery_is_period_safe_and_non_operational() -> None:
    inventory_id, inventory_name, period = _selected_inventory()
    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/entrega-profesional")

    assert response.status_code == 200
    assert inventory_name in response.text
    assert period in response.text
    assert "Consulta explícita del periodo" in response.text
    assert "no aprueba, no cierra, no publica" in response.text
    assert "no equivale a verificación independiente" in response.text

    soup = BeautifulSoup(response.text, "html.parser")
    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == f"/inventarios/{inventory_id}"
    assert not soup.select("form")
    assert not soup.select(".delivery-gates a")
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}/reportes"]') is not None
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}/reduccion"]') is not None
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None

    forbidden_exact = {
        "/calculos",
        "/analisis",
        "/reduccion",
        "/reportes",
        "/control",
        "/informacion",
        "/entrega-profesional",
    }
    rendered_hrefs = {link.get("href") for link in soup.select("a[href]")}
    assert not (forbidden_exact & rendered_hrefs)

    gates = soup.select("section.card .delivery-gate")
    assert len(gates) >= 8


def test_v238d2_default_delivery_remains_operational() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/entrega-profesional")

    assert response.status_code == 200
    assert "Consulta explícita del periodo" not in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one('a[href="/reportes"]') is not None or soup.select_one('a[href="/control"]') is not None


def test_v238d2_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/entrega-profesional")

    assert response.status_code == 404
