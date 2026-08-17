from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, SessionLocal
from app.inventory_context import get_inventory
from app.main import app
from app.repositories.inventories import list_inventories


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v219_recent_period_order_matches_default_inventory_authority() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        user = {"organization_id": db_user.organization_id}
        ordered = list_inventories(session, db_user.organization_id)
        default_inventory = get_inventory(session, user)
        assert ordered
        assert ordered[0].id == default_inventory.id


def test_v219_inventory_list_marks_exactly_one_default_context() -> None:
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.get("/inventarios")
        assert response.status_code == 200
        assert response.text.count("PERIODO MÁS RECIENTE · CONTEXTO POR DEFECTO") == 1
        assert "Abrir periodo" in response.text
        assert "cuando una ruta no especifica inventario" in response.text


def test_v219_inventory_detail_never_invents_pending_decisions_for_client() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        alias = client.get("/inventario", follow_redirects=False)
        assert alias.status_code == 303
        detail = client.get(alias.headers["location"])
        assert detail.status_code == 200
        soup = BeautifulSoup(detail.text, "html.parser")
        head = soup.select_one(".inventory-head")
        side = soup.select_one(".side-stack")
        assert head is not None and side is not None
        assert "Ver fuentes" in head.get_text(" ", strip=True)
        assert "Gestionar fuentes" not in head.get_text(" ", strip=True)
        side_text = side.get_text(" ", strip=True)
        assert "Decisiones pendientes" not in side_text
        assert "Confirmar relevancia de transporte contratado" not in side_text
        assert "Documentar el tratamiento de fuentes inferiores al 5%" not in side_text
        assert "ETAPA ACTUAL" in side_text
        assert "Esta ficha no presume decisiones pendientes" in side_text


def test_v219_inventory_detail_preserves_source_management_for_consultant() -> None:
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        alias = client.get("/inventario", follow_redirects=False)
        assert alias.status_code == 303
        detail = client.get(alias.headers["location"])
        assert detail.status_code == 200
        soup = BeautifulSoup(detail.text, "html.parser")
        head = soup.select_one(".inventory-head")
        assert head is not None
        assert "Gestionar fuentes" in head.get_text(" ", strip=True)
