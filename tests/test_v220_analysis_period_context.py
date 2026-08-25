from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, SessionLocal
from app.inventory_context import get_inventory
from app.main import app


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v220_analysis_uses_default_period_authority_without_active_inventory_copy() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        inventory = get_inventory(session, {"organization_id": db_user.organization_id})
        expected_period = (
            f"Periodo {inventory.start_date.strftime('%d/%m/%Y')} – "
            f"{inventory.end_date.strftime('%d/%m/%Y')}"
        )
        inventory_name = inventory.name

    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.get("/analisis")

    assert response.status_code == 200
    assert inventory_name in response.text
    assert expected_period in response.text
    assert "Lectura ejecutiva · contexto por periodo" in response.text
    assert "inventario activo" not in response.text.lower()
