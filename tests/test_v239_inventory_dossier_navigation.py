from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal
from app.main import app

pytestmark = pytest.mark.smoke


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _historical_inventory_id() -> int:
    with SessionLocal() as session:
        user = session.scalar(
            select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local")
        )
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.asc(), Inventory.id.asc())
        )
        assert inventory is not None
        return inventory.id


def test_v239_dossier_navigation_preserves_explicit_inventory_context() -> None:
    inventory_id = _historical_inventory_id()
    root = f"/inventarios/{inventory_id}"
    dossier_paths = [
        root,
        f"{root}/informacion",
        f"{root}/calculos",
        f"{root}/analisis",
        f"{root}/reduccion",
        f"{root}/reportes",
        f"{root}/entrega-profesional",
    ]

    with TestClient(app) as client:
        _login(client)
        for path in dossier_paths:
            response = client.get(path)
            assert response.status_code == 200, path
            soup = BeautifulSoup(response.text, "html.parser")
            nav = soup.select_one("[data-inventory-dossier-nav]")
            assert nav is not None, path

            links = nav.find_all("a")
            assert len(links) == 7
            assert [link.get("href") for link in links] == dossier_paths
            assert all(
                str(link.get("href") or "").startswith(f"/inventarios/{inventory_id}")
                for link in links
            )

            current = nav.select('a[aria-current="page"]')
            assert len(current) == 1
            assert current[0].get("href") == path


def test_v239_general_routes_do_not_claim_an_explicit_dossier_context() -> None:
    generic_paths = [
        "/informacion",
        "/calculos",
        "/analisis",
        "/reduccion",
        "/reportes",
        "/entrega-profesional",
    ]

    with TestClient(app) as client:
        _login(client)
        for path in generic_paths:
            response = client.get(path, follow_redirects=True)
            assert response.status_code == 200, path
            soup = BeautifulSoup(response.text, "html.parser")
            assert soup.select_one("[data-inventory-dossier-nav]") is None, path
