from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import (
    ActivityFactorSelection,
    Base,
    EmissionCalculation,
    EmissionFactorVersion,
    EmissionSource,
    ENGINE,
    SessionLocal,
    SupportMessage,
    SupportTicket,
    init_db,
)
from app.factor_advisor import advise_factor
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_v050():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def first_activity_context():
    with SessionLocal() as session:
        source = session.scalar(
            select(EmissionSource)
            .where(EmissionSource.activity_records.any())
            .options(selectinload(EmissionSource.activity_records), selectinload(EmissionSource.inventory))
        )
        assert source and source.activity_records
        record = source.activity_records[0]
        return source.inventory_id, source.id, record.id


def test_v050_support_request_has_context_reference_sla_and_initial_message():
    inventory_id, source_id, record_id = first_activity_context()
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        response = client.post(
            "/soporte/nuevo",
            data={
                "request_type": "Decisión metodológica",
                "category": "Revisión de factor",
                "priority": "Alta",
                "subject": "Confirmar factor para consumo de papel",
                "description": "Necesitamos validar la unidad, el tipo de papel y el factor aplicable al dato cargado.",
                "desired_outcome": "Factor aprobado con justificación reproducible.",
                "inventory_id": str(inventory_id),
                "source_id": str(source_id),
                "activity_data_id": str(record_id),
                "due_date": "2026-08-15",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/soporte/")

    with SessionLocal() as session:
        ticket = session.scalar(
            select(SupportTicket)
            .where(SupportTicket.subject == "Confirmar factor para consumo de papel")
            .options(selectinload(SupportTicket.messages))
        )
        assert ticket is not None
        assert ticket.public_reference.startswith("CTH-2026-")
        assert ticket.inventory_id == inventory_id
        assert ticket.source_id == source_id
        assert ticket.activity_data_id == record_id
        assert ticket.assigned_to == "Revisor metodológico"
        assert ticket.response_due_at is not None
        created = ticket.created_at if ticket.created_at.tzinfo else ticket.created_at.replace(tzinfo=UTC)
        due = ticket.response_due_at if ticket.response_due_at.tzinfo else ticket.response_due_at.replace(tzinfo=UTC)
        assert 11.5 <= (due - created).total_seconds() / 3600 <= 12.5
        assert len(ticket.messages) == 1
        assert ticket.messages[0].message_type == "Solicitud inicial"


def test_v050_support_conversation_hides_internal_notes_from_client_and_updates_status():
    with TestClient(app) as admin:
        login(admin, "admin@calculatuhuella.local")
        created = admin.post(
            "/soporte/nuevo",
            data={
                "request_type": "Consulta",
                "category": "Duda metodológica",
                "priority": "Normal",
                "subject": "Revisar tratamiento del dato estimado",
                "description": "Se requiere confirmar si el dato estimado puede mantenerse en el cierre mensual.",
                "desired_outcome": "Criterio documentado para el cierre.",
            },
            follow_redirects=False,
        )
        ticket_id = int(created.headers["location"].rsplit("/", 1)[-1])
        internal = admin.post(
            f"/soporte/{ticket_id}/mensajes",
            data={"body": "Validar primero la evidencia del mes anterior.", "message_type": "Nota interna"},
            follow_redirects=False,
        )
        assert internal.status_code == 303
        public = admin.post(
            f"/soporte/{ticket_id}/mensajes",
            data={
                "body": "Solicitamos adjuntar el soporte y explicar la base de estimación.",
                "message_type": "Solicitud de información",
                "visible_to_client": "1",
                "next_status": "Esperando cliente",
            },
            follow_redirects=False,
        )
        assert public.status_code == 303

        detail_admin = admin.get(f"/soporte/{ticket_id}")
        assert "Validar primero la evidencia" in detail_admin.text
        assert "Solicitamos adjuntar" in detail_admin.text

    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        detail_client = client.get(f"/soporte/{ticket_id}")
        assert detail_client.status_code == 200
        assert "Validar primero la evidencia" not in detail_client.text
        assert "Solicitamos adjuntar" in detail_client.text
        reply = client.post(
            f"/soporte/{ticket_id}/mensajes",
            data={"body": "Adjuntaremos el soporte y la memoria de estimación hoy."},
            follow_redirects=False,
        )
        assert reply.status_code == 303

    with SessionLocal() as session:
        ticket = session.get(SupportTicket, ticket_id)
        assert ticket.status == "En gestión"
        messages = list(session.scalars(select(SupportMessage).where(SupportMessage.ticket_id == ticket_id)))
        assert len(messages) == 4
        assert any(not item.visible_to_client for item in messages)


def test_v050_factor_proposal_requires_review_before_affecting_calculation():
    with SessionLocal() as session:
        sources = list(session.scalars(
            select(EmissionSource)
            .where(EmissionSource.activity_records.any())
            .options(
                selectinload(EmissionSource.activity_records),
                selectinload(EmissionSource.factor_assignments),
            )
        ))
        versions = list(session.scalars(
            select(EmissionFactorVersion).options(
                selectinload(EmissionFactorVersion.factor),
                selectinload(EmissionFactorVersion.gas),
            )
        ))
        chosen = None
        for source in sources:
            assigned_ids = {item.factor_version_id for item in source.factor_assignments if item.active}
            for record in source.activity_records:
                candidates = [
                    (advise_factor(session, source, record, version), version)
                    for version in versions if version.id not in assigned_ids
                ]
                candidates = [item for item in candidates if item[0]["calculable"] and item[0]["score"] >= 55]
                if candidates:
                    candidates.sort(key=lambda item: item[0]["score"], reverse=True)
                    chosen = source.id, record.id, candidates[0][1].id
                    break
            if chosen:
                break
        assert chosen is not None
        source_id, record_id, factor_id = chosen

    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        proposed = client.post(
            f"/fuentes/{source_id}/datos/{record_id}/factores/seleccionar",
            data={
                "factor_version_id": factor_id,
                "rationale": "La actividad, unidad y periodo son compatibles; se propone para revisión metodológica.",
            },
            follow_redirects=False,
        )
        assert proposed.status_code == 303

    with SessionLocal() as session:
        selection = session.scalar(select(ActivityFactorSelection).where(
            ActivityFactorSelection.activity_data_id == record_id,
            ActivityFactorSelection.factor_version_id == factor_id,
        ))
        assert selection is not None
        assert selection.selection_status == "Propuesto"
        assert selection.applied_at is None
        calculations = list(session.scalars(select(EmissionCalculation).where(EmissionCalculation.activity_data_id == record_id)))
        assert factor_id not in {item.factor_version_id for item in calculations}
        selection_id = selection.id

    with TestClient(app) as reviewer:
        login(reviewer, "revisor@calculatuhuella.local")
        approved = reviewer.post(
            f"/fuentes/{source_id}/datos/{record_id}/factores/{selection_id}/revisar",
            data={
                "decision": "Aprobar",
                "review_notes": "Se valida unidad, representatividad sectorial y ausencia de doble conteo.",
            },
            follow_redirects=False,
        )
        assert approved.status_code == 303
        api = reviewer.get(f"/api/fuentes/{source_id}/datos/{record_id}/factores")
        assert api.status_code == 200
        assert api.json()["control_status"] in {"Aprobado", "Aprobado con alertas"}

    with SessionLocal() as session:
        selection = session.get(ActivityFactorSelection, selection_id)
        assert selection.selection_status == "Aprobado"
        assert selection.reviewed_by == "revisor@calculatuhuella.local"
        assert selection.review_notes
        assert selection.applied_at is not None
        calculations = list(session.scalars(select(EmissionCalculation).where(EmissionCalculation.activity_data_id == record_id)))
        assert factor_id in {item.factor_version_id for item in calculations}


def test_v050_support_page_api_and_release_metadata_are_aligned():
    root = Path(__file__).resolve().parents[1]
    with TestClient(app) as client:
        login(client, "admin@calculatuhuella.local")
        page = client.get("/soporte")
        assert page.status_code == 200
        assert "Centro de conversaciones y requerimientos" in page.text
        assert "Prioridad y SLA" in page.text
        summary = client.get("/api/soporte/resumen")
        assert summary.status_code == 200
        assert summary.json()["version"] == "1.0.0"
    assert (root / "migrations/versions/20260804_0031_v050_support_conversation.py").is_file()
    assert (root / "app/templates/support_detail.html").is_file()
    assert len(Base.metadata.tables) == 120
