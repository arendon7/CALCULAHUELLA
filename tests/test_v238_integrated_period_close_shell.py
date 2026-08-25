from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app import period_close_web
from app.main import app


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v238_monthly_close_without_pilot_inventory_uses_neutral_shell(monkeypatch) -> None:
    monkeypatch.setattr(
        period_close_web,
        "period_close_summary",
        lambda session, organization_id, period: {
            "execution": None,
            "inventory": None,
        },
    )

    with TestClient(app) as client:
        login(client)
        response = client.get("/cierre-mensual")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.select_one("h1")
    assert heading is not None
    assert "Cierre mensual del piloto" in heading.get_text(" ", strip=True)

    pill = soup.select_one(".topbar .version-pill")
    assert pill is not None
    assert pill.get("href") == "/inventario"
    assert "Ver por defecto" in pill.get_text(" ", strip=True)
