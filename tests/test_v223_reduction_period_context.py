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


def test_v223_reduction_uses_explicit_period_and_no_legacy_version_copy() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        inventory = get_inventory(session, {"organization_id": db_user.organization_id})
        expected_period = (
            f"Periodo {inventory.start_date.strftime('%d/%m/%Y')} – "
            f"{inventory.end_date.strftime('%d/%m/%Y')}"
        )

    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.get("/reduccion")

    assert response.status_code == 200
    assert expected_period in response.text
    assert "Decisiones cuantificadas · seguimiento de ejecución" in response.text
    assert "Huella bruta del periodo usada para dimensionar el portafolio" in response.text
    assert "V0.55" not in response.text
