from __future__ import annotations

from datetime import timedelta

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    ActivityData,
    AppUser,
    DataRequest,
    EmissionSource,
    EvidenceDocument,
    Inventory,
    SessionLocal,
)
from app.main import app


SELECTED_REQUEST = "V238E-SELECTED-REQUEST"
OTHER_REQUEST = "V238E-OTHER-REQUEST"
SELECTED_EVIDENCE = "V238E-SELECTED-EVIDENCE.pdf"
OTHER_EVIDENCE = "V238E-OTHER-EVIDENCE.pdf"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _prepare_records() -> dict[str, object]:
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

        selected_source = EmissionSource(
            inventory_id=selected.id,
            name="V238E selected source",
            scope=1,
            category="Combustión estacionaria",
        )
        other_source = EmissionSource(
            inventory_id=other.id,
            name="V238E other source",
            scope=1,
            category="Combustión estacionaria",
        )
        session.add_all([selected_source, other_source])
        session.flush()

        selected_evidence = EvidenceDocument(
            inventory_id=selected.id,
            source_id=selected_source.id,
            name=SELECTED_EVIDENCE,
            stored_name="tests/v238e-selected.pdf",
            document_type="Factura",
            source_name=selected_source.name,
            period_label=str(selected.start_date.year),
            uploaded_by=user.email,
            file_size=128,
            sha256="a" * 64,
        )
        other_evidence = EvidenceDocument(
            inventory_id=other.id,
            source_id=other_source.id,
            name=OTHER_EVIDENCE,
            stored_name="tests/v238e-other.pdf",
            document_type="Factura",
            source_name=other_source.name,
            period_label=str(other.start_date.year),
            uploaded_by=user.email,
            file_size=256,
            sha256="b" * 64,
        )
        session.add_all([selected_evidence, other_evidence])
        session.flush()

        selected_record = ActivityData(
            source_id=selected_source.id,
            evidence_id=selected_evidence.id,
            period_start=selected.start_date,
            period_end=min(selected.end_date, selected.start_date + timedelta(days=30)),
            value=238.01,
            unit="kWh",
            data_origin="Factura",
            quality_level="A",
            created_by=user.email,
        )
        other_record = ActivityData(
            source_id=other_source.id,
            evidence_id=other_evidence.id,
            period_start=other.start_date,
            period_end=min(other.end_date, other.start_date + timedelta(days=30)),
            value=238.02,
            unit="kWh",
            data_origin="Factura",
            quality_level="A",
            created_by=user.email,
        )
        selected_request = DataRequest(
            inventory_id=selected.id,
            source_id=selected_source.id,
            title=SELECTED_REQUEST,
            source_name=selected_source.name,
            requested_to="Contabilidad",
            due_date=selected.start_date + timedelta(days=15),
            status="Pendiente",
            instructions="Solicitud aislada del periodo seleccionado.",
        )
        other_request = DataRequest(
            inventory_id=other.id,
            source_id=other_source.id,
            title=OTHER_REQUEST,
            source_name=other_source.name,
            requested_to="Contabilidad",
            due_date=other.start_date + timedelta(days=15),
            status="Pendiente",
            instructions="Solicitud del otro periodo.",
        )
        session.add_all([selected_record, other_record, selected_request, other_request])
        session.commit()

        return {
            "inventory_id": selected.id,
            "inventory_name": selected.name,
            "period": f"{selected.start_date.strftime('%d/%m/%Y')} – {selected.end_date.strftime('%d/%m/%Y')}",
            "selected_record_id": selected_record.id,
            "other_record_id": other_record.id,
            "selected_evidence_id": selected_evidence.id,
            "other_evidence_id": other_evidence.id,
            "selected_request_id": selected_request.id,
            "other_request_id": other_request.id,
            "source_ids": [selected_source.id, other_source.id],
        }


def _cleanup(data: dict[str, object]) -> None:
    with SessionLocal() as session:
        for record_id in [data["selected_record_id"], data["other_record_id"]]:
            record = session.get(ActivityData, int(record_id))
            if record is not None:
                session.delete(record)
        for request_id in [data["selected_request_id"], data["other_request_id"]]:
            item = session.get(DataRequest, int(request_id))
            if item is not None:
                session.delete(item)
        for evidence_id in [data["selected_evidence_id"], data["other_evidence_id"]]:
            item = session.get(EvidenceDocument, int(evidence_id))
            if item is not None:
                session.delete(item)
        session.flush()
        for source_id in data["source_ids"]:
            source = session.get(EmissionSource, int(source_id))
            if source is not None:
                session.delete(source)
        session.commit()


def test_v238e_scoped_information_is_isolated_and_read_only() -> None:
    data = _prepare_records()
    try:
        inventory_id = int(data["inventory_id"])
        with TestClient(app) as client:
            login(client)
            response = client.get(f"/inventarios/{inventory_id}/informacion")

        assert response.status_code == 200
        assert str(data["inventory_name"]) in response.text
        assert str(data["period"]) in response.text
        assert SELECTED_REQUEST in response.text
        assert OTHER_REQUEST not in response.text
        assert SELECTED_EVIDENCE in response.text
        assert OTHER_EVIDENCE not in response.text
        assert "Consulta explícita del periodo" in response.text

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.select_one("#contenido-aplicacion")
        assert content is not None
        pill = soup.select_one(".topbar .version-pill")
        assert pill is not None
        assert pill.get("href") == f"/inventarios/{inventory_id}"
        assert not content.select("form")
        assert content.select_one(f'[data-record-id="{data["selected_record_id"]}"]') is not None
        assert content.select_one(f'[data-record-id="{data["other_record_id"]}"]') is None
        assert content.select_one(f'[data-request-id="{data["selected_request_id"]}"]') is not None
        assert content.select_one(f'[data-request-id="{data["other_request_id"]}"]') is None
        assert content.select_one(f'[data-evidence-id="{data["selected_evidence_id"]}"]') is not None
        assert content.select_one(f'[data-evidence-id="{data["other_evidence_id"]}"]') is None
        assert content.select_one(f'a[href="/evidencias/{data["selected_evidence_id"]}/descargar"]') is not None

        forbidden_exact = {
            "/informacion",
            "/captura-guiada",
            "/informacion/importar",
            "/informacion/plantilla.xlsx",
            "/calculos",
            "/analisis",
            "/reduccion",
            "/reportes",
            "/entrega-profesional",
        }
        rendered_hrefs = {link.get("href") for link in content.select("a[href]")}
        assert not (forbidden_exact & rendered_hrefs)
    finally:
        _cleanup(data)


def test_v238e_inventory_record_exposes_scoped_information() -> None:
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
    assert soup.select_one(f'a[href="/inventarios/{inventory_id}/informacion"]') is not None


def test_v238e_default_information_remains_operational() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/informacion")

    assert response.status_code == 200
    assert "Consulta explícita del periodo" not in response.text
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.select_one('a[href="/informacion/importar"]') is not None
    assert soup.select_one('a[href="/informacion/plantilla.xlsx"]') is not None


def test_v238e_unknown_inventory_is_not_resolved_to_default() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/999999999/informacion")

    assert response.status_code == 404
