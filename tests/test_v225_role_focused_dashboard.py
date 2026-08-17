from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def focused_journey_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    journey = soup.select_one('[data-role-focused-journey="true"]')
    assert journey is not None
    return journey.get_text(" ", strip=True)


def test_v225_client_dashboard_hides_other_role_stage_noise_without_hiding_full_process() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        response = client.get("/dashboard")

    assert response.status_code == 200
    journey_text = focused_journey_text(response.text)
    assert "las etapas de otros roles siguen formando parte del inventario" in journey_text
    assert "Ver recorrido completo" in journey_text
    assert "· otro rol" not in journey_text


def test_v225_verifier_dashboard_uses_same_focused_journey_contract() -> None:
    with TestClient(app) as client:
        login(client, "verificador@calculatuhuella.local")
        response = client.get("/dashboard")

    assert response.status_code == 200
    journey_text = focused_journey_text(response.text)
    assert "Ver recorrido completo" in journey_text
    assert "· otro rol" not in journey_text


def test_v225_consultant_preserves_cross_role_process_visibility() -> None:
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'data-role-focused-journey="true"' not in response.text
    assert "TU RUTA DE TRABAJO" in response.text
