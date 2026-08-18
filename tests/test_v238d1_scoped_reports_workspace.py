from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AppUser, Inventory, ReportArtifact, SessionLocal
from app.main import app


SELECTED_MARKER = "V238D1-SELECTED-REPORT"
OTHER_MARKER = "V238D1-OTHER-REPORT"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _prepare_artifacts() -> tuple[int, str, str, list[int]]:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventories = list(
            session.scalars(
                select(Inventory)
                .where(Inventory.organization_id == user.organization_id)
                .order_by(Inventory.start_date.asc(), Inventory.id.asc())
            )
        )
        assert len(inventories) >= 2
        selected = inventories[0]
        other = inventories[-1]
        if other.id == selected.id:
            other = inventories[1]

        artifacts = [
            ReportArtifact(
                inventory_id=selected.id,
                report_type=SELECTED_MARKER,
                version="v238d1-selected",
                status="Generado",
                file_name="v238d1-selected.pdf",
                stored_name="v238d1-selected.pdf",
                file_size=128,
                sha256="a" * 64,
                generated_by=user.email,
            ),
            ReportArtifact(
                inventory_id=other.id,
                report_type=OTHER_MARKER,
                version="v238d1-other",
                status="Generado",
                file_name="v238d1-other.pdf",
                stored_name="v238d1-other.pdf",
                file_size=256,
                sha256="b" * 64,
                generated_by=user.email,
            ),
        ]
        session.add_all(artifacts)
        session.commit()
        ids = [item.id for item in artifacts]
        period = f"{selected.start_date.strftime('%d/%m/%Y')} – {selected.end_date.strftime('%d/%m/%Y')}"
        return selected.id, selected.name, period, ids


def _cleanup_artifacts(ids: list[int]) -> None:
    with SessionLocal() as session:
        for artifact_id in ids:
            artifact = session.get(ReportArtifact, artifact_id)
            if artifact is not None:
                session.delete(artifact)
        session.commit()


def test_v238d1_scoped_reports_are_isolated_to_requested_inventory() -> None:
    inventory_id, inventory_name, period, artifact_ids = _prepare_artifacts()
    try:
        with TestClient(app) as client:
            login(client)
            response = client.get(f"/inventarios/{inventory_id}/reportes")

        assert response.status_code == 200
        assert inventory_name in response.text
        assert period in response.text
        assert SELECTED_MARKER in response.text
        assert OTHER_MARKER not in response.text
        assert "Consulta explícita del periodo" in response.text

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.select_one("#contenido-aplicacion")
        assert content is not None
        pill = soup.select_one(".topbar .version-pill")
        assert pill is not None
        assert pill.get("href") == f"/inventarios/{inventory_id}"
        assert not content.select('form[method="post"]')
        assert content.select_one('a[href="/entrega-profesional"]') is None
        assert content.select_one('a[href="/reportes/consultoria"]') is None
        assert content.select_one('a[href="/control"]') is None
        assert content.select_one(f'a[href="/inventarios/{inventory_id}/reduccion"]') is not None
        assert content.select_one(f'a[href="/inventarios/{inventory_id}"]') is not None
        assert content.select_one(f'a[href="/reportes/{artifact_ids[0]}/descargar"]') is not None
        assert "no equivale a verificación independiente" in response.text
    finally:
        _cleanup_artifacts(artifact_ids)


def test_v238d1_inventory_record_exposes_scoped_reports() -> None:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.asc(), Inventory.id.asc())
        )
        assert inventory is not None
        inventory_id = inventory.id

    with TestClient(app) as client:
        login(client)
        response = client.get(f"/inventarios/{inventory_id}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}/reportes"]') is not None


def test_v238d1_default_reports_preserve_operational_tools() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/reportes")

    assert response.status_code == 200
    assert "Consulta explícita del periodo" not in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one('a[href="/reportes/consultoria"]') is not None
    assert soup.select_one('a[href="/entrega-profesional"]') is not None
    assert soup.select_one('form[action="/reportes/generar"]') is not None


def test_v238d1_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/reportes")

    assert response.status_code == 404
