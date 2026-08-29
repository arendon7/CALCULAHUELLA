from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, SessionLocal
from app.inventory_context import get_inventory
from app.main import app


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v227_delivery_explains_calculated_reviewed_and_publishable_as_distinct_states() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        inventory = get_inventory(session, {"organization_id": db_user.organization_id})
        expected_period = (
            f"Periodo {inventory.start_date.strftime('%d/%m/%Y')} – "
            f"{inventory.end_date.strftime('%d/%m/%Y')}"
        )

    with TestClient(app) as client:
        login(client)
        response = client.get("/entrega-profesional")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    maturity = soup.select_one("[data-result-maturity]")
    assert maturity is not None
    assert expected_period in response.text
    assert "Calculado no significa automáticamente revisado ni publicable" in maturity.get_text(" ", strip=True)
    assert len(maturity.select("[data-result-stage]")) == 3
    assert maturity.select_one('[data-result-stage="calculated"]') is not None
    assert maturity.select_one('[data-result-stage="reviewed"]') is not None
    assert maturity.select_one('[data-result-stage="publishable"]') is not None
    assert "Cuantificado" in maturity.get_text(" ", strip=True)
    assert "Revisado y aprobado" in maturity.get_text(" ", strip=True)
    assert "Publicable" in maturity.get_text(" ", strip=True)
    assert "no equivale a una verificación independiente" in maturity.get_text(" ", strip=True)


def test_v227_maturity_view_keeps_existing_publication_authority_visible() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/entrega-profesional")

    assert response.status_code == 200
    assert "NIVEL DE PUBLICACIÓN" in response.text
    assert "CONTROL DE USO Y PUBLICACIÓN" in response.text
    assert "OCHO PUERTAS DE CONTROL" in response.text
