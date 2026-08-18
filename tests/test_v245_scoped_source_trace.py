from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, EmissionSource, Inventory, SessionLocal
from app.main import app


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _source_context() -> tuple[int, int, int]:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory_ids = list(
            session.scalars(
                select(Inventory.id)
                .where(Inventory.organization_id == user.organization_id)
                .order_by(Inventory.start_date.asc(), Inventory.id.asc())
            )
        )
        assert len(inventory_ids) >= 2
        for inventory_id in inventory_ids:
            source_id = session.scalar(
                select(EmissionSource.id)
                .where(EmissionSource.inventory_id == inventory_id)
                .order_by(EmissionSource.id.asc())
            )
            if source_id is not None:
                other_inventory_id = next(item for item in inventory_ids if item != inventory_id)
                return inventory_id, source_id, other_inventory_id
    raise AssertionError("El seed demo no contiene una fuente utilizable para V2.45")


def test_v245_scoped_source_is_read_only_and_keeps_period_navigation() -> None:
    inventory_id, source_id, _ = _source_context()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}/fuentes/{source_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one("[data-scoped-source-readonly]") is not None
    assert soup.select_one(f'.version-pill[href="/inventarios/{inventory_id}"]') is not None

    content = soup.select_one("#contenido-aplicacion")
    assert content is not None
    assert content.select_one('form[method="post"]') is None
    assert content.select_one(f'form[action="/fuentes/{source_id}/recalcular"]') is None
    assert content.select_one(f'form[action="/fuentes/{source_id}/configurar"]') is None
    assert content.select_one('[data-inventory-dossier-nav]') is None

    sidebar_hrefs = {link.get("href") for link in soup.select("#navegacion-principal a[href]")}
    assert f"/inventarios/{inventory_id}/informacion" in sidebar_hrefs
    assert f"/inventarios/{inventory_id}/calculos" in sidebar_hrefs
    assert f"/inventarios/{inventory_id}/analisis" in sidebar_hrefs
    assert f"/inventarios/{inventory_id}/reduccion" in sidebar_hrefs
    assert f"/inventarios/{inventory_id}/reportes" in sidebar_hrefs
    assert f"/inventarios/{inventory_id}/entrega-profesional" in sidebar_hrefs
    assert "/calculos" not in sidebar_hrefs
    assert "/informacion" not in sidebar_hrefs


def test_v245_scoped_source_rejects_inventory_source_mismatch() -> None:
    inventory_id, source_id, other_inventory_id = _source_context()
    assert other_inventory_id != inventory_id

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{other_inventory_id}/fuentes/{source_id}")

    assert response.status_code == 404


def test_v245_operational_source_route_remains_editable_for_authorized_consultant() -> None:
    _, source_id, _ = _source_context()

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/fuentes/{source_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one("[data-scoped-source-readonly]") is None
    assert soup.select_one(f'form[action="/fuentes/{source_id}/recalcular"]') is not None


def test_v245_results_choose_scoped_or_operational_source_trace_by_context() -> None:
    inventory_id, source_id, _ = _source_context()

    with TestClient(app) as client:
        login(client)
        scoped = client.get(f"/inventarios/{inventory_id}/calculos")
        generic = client.get("/calculos")

    assert scoped.status_code == 200
    scoped_soup = BeautifulSoup(scoped.text, "html.parser")
    scoped_links = scoped_soup.select('a[data-scoped-source-link="true"]')
    assert scoped_links
    assert all(
        (link.get("href") or "").startswith(f"/inventarios/{inventory_id}/fuentes/")
        for link in scoped_links
    )
    assert scoped_soup.select_one(f'a[href="/inventarios/{inventory_id}/fuentes/{source_id}"]') is not None

    assert generic.status_code == 200
    generic_soup = BeautifulSoup(generic.text, "html.parser")
    assert generic_soup.select_one('a[data-scoped-source-link="true"]') is None
    assert generic_soup.select_one(f'a[href="/fuentes/{source_id}"]') is not None
