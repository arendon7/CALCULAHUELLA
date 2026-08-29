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


def test_v228_period_list_distinguishes_default_from_historical_consultation() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios")

    assert response.status_code == 200
    assert response.text.count("PERIODO MÁS RECIENTE · CONTEXTO POR DEFECTO") == 1
    assert "Abrir periodo por defecto" in response.text
    assert "Consulta histórica sin cambiar el contexto por defecto" in response.text
    assert "Consultar esta ficha no cambia el periodo por defecto" in response.text
    assert "Consultar periodo histórico" in response.text


def test_v228_explicit_period_detail_warns_that_general_routes_keep_latest_default() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert db_user is not None
        inventories = list(
            session.scalars(
                select(Inventory)
                .where(Inventory.organization_id == db_user.organization_id)
                .order_by(Inventory.start_date.desc(), Inventory.id.desc())
            )
        )
        assert inventories
        explicit_inventory = inventories[-1]

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{explicit_inventory.id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    context = soup.select_one("[data-explicit-period-context]")
    content = soup.select_one("#contenido-aplicacion")
    assert context is not None and content is not None
    context_text = context.get_text(" ", strip=True)
    assert "Expediente del periodo · contexto fijado por URL" in context_text
    assert "Las rutas generales de la aplicación continúan resolviendo el periodo más reciente por defecto" in context_text
    assert context.select_one('a[href="/inventarios"]') is not None
    assert context.select_one('a[href="/recorrido-inventario"]') is not None
    assert "Ver periodos y contexto por defecto" in context_text
    assert "Abrir recorrido por defecto" in context_text
