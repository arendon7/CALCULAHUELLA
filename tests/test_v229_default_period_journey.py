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


def test_v229_journey_declares_latest_period_as_default_workflow_context() -> None:
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
        response = client.get("/recorrido-inventario")

    assert response.status_code == 200
    assert expected_period in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    context = soup.select_one("[data-default-period-journey]")
    assert context is not None
    text = context.get_text(" ", strip=True)
    assert "Recorrido del periodo por defecto" in text
    assert "el periodo más reciente de la organización" in text
    assert "Consultar un periodo histórico no sustituye este contexto" in text
    assert context.select_one('a[href="/inventarios"]') is not None
