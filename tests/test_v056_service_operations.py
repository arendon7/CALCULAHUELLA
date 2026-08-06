from __future__ import annotations

import re

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import (
    AppUser,
    Base,
    ENGINE,
    OrganizationMembership,
    OrganizationSubscription,
    SessionLocal,
    UserInvitation,
    init_db,
)
from app.main import app
from app.service_operations import capacity_snapshot, ensure_capacity, operation_summary


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def test_v056_operation_center_and_api_explain_capacity():
    with TestClient(app) as client:
        login(client)
        page = client.get("/operacion-servicio")
        assert page.status_code == 200
        assert "Centro de operación del servicio" in page.text
        assert "Próxima decisión" in page.text or "PRÓXIMA DECISIÓN" in page.text
        api = client.get("/api/operacion-servicio/resumen")
        assert api.status_code == 200
        payload = api.json()
        assert payload["subscription"]["status"] in {"Activa", "Prueba"}
        assert set(payload["capacity"]) == {"users", "facilities", "inventories", "storage"}


def test_v056_secure_invitation_can_be_accepted_once():
    with TestClient(app) as admin_client:
        login(admin_client)
        response = admin_client.post(
            "/usuarios/invitar",
            data={"name": "Nueva Responsable", "email": "nueva@empresa.co", "role": "Cliente", "validity_days": "7"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = admin_client.get("/usuarios")
        assert "nueva@empresa.co" in page.text
        match = re.search(r'value="([^"]+/invitacion/[^\"]+)"', page.text)
        assert match, page.text[:1000]
        invite_url = match.group(1)

    token_path = "/invitacion/" + invite_url.rsplit("/", 1)[-1]
    with TestClient(app) as invitee:
        landing = invitee.get(token_path)
        assert landing.status_code == 200
        assert "Invitación segura" in landing.text or "INVITACIÓN SEGURA" in landing.text
        accepted = invitee.post(
            token_path + "/aceptar",
            data={"name": "Nueva Responsable", "password": "ClaveSegura2026!"},
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        assert accepted.headers["location"] == "/dashboard"
        second = invitee.post(
            token_path + "/aceptar",
            data={"name": "Nueva Responsable", "password": "ClaveSegura2026!"},
            follow_redirects=False,
        )
        assert second.status_code == 409

    with SessionLocal() as session:
        invitation = session.scalar(select(UserInvitation).where(UserInvitation.email == "nueva@empresa.co"))
        assert invitation is not None and invitation.status == "Aceptada"
        user = session.scalar(select(AppUser).where(AppUser.email == "nueva@empresa.co"))
        assert user is not None
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == invitation.organization_id,
        ))
        assert membership is not None and membership.role == "Cliente" and membership.active


def test_v056_pending_invitation_reserves_plan_capacity():
    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == 1))
        snapshot = capacity_snapshot(session, 1)
        subscription.plan.max_users = int(snapshot["metrics"]["users"]["value"])
        session.commit()
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/usuarios/invitar",
            data={"name": "Sin cupo", "email": "sincupo@empresa.co", "role": "Cliente", "validity_days": "7"},
            follow_redirects=False,
        )
        assert response.status_code == 409
        assert "límite" in response.text.lower()


def test_v056_capacity_guard_blocks_only_new_resources():
    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == 1))
        snapshot = capacity_snapshot(session, 1)
        subscription.plan.max_inventories = int(snapshot["metrics"]["inventories"]["value"])
        session.commit()
        with pytest.raises(HTTPException) as error:
            ensure_capacity(session, 1, "inventories", 1)
        assert error.value.status_code == 409
        # Existing information remains available and the operational summary can still be built.
        summary = operation_summary(session, 1)
        assert summary["metrics"]["inventories"]["status"] == "blocked"
        assert summary["actions"]


def test_v056_model_and_migration_are_registered():
    assert "user_invitations" in Base.metadata.tables
    with SessionLocal() as session:
        assert session.scalar(select(func.count(UserInvitation.id))) == 0


def test_v056_invitation_acceptance_rechecks_downgraded_plan():
    with TestClient(app) as admin_client:
        login(admin_client)
        response = admin_client.post(
            "/usuarios/invitar",
            data={"name": "Cupo reservado", "email": "reserva@empresa.co", "role": "Cliente", "validity_days": "7"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = admin_client.get("/usuarios")
        match = re.search(r'value="([^"]+/invitacion/[^\"]+)"', page.text)
        assert match
        token_path = "/invitacion/" + match.group(1).rsplit("/", 1)[-1]

    with SessionLocal() as session:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == 1))
        snapshot = capacity_snapshot(session, 1)
        subscription.plan.max_users = max(1, int(snapshot["metrics"]["users"]["value"]) - 1)
        session.commit()

    with TestClient(app) as invitee:
        response = invitee.post(
            token_path + "/aceptar",
            data={"name": "Cupo reservado", "password": "ClaveSegura2026!"},
            follow_redirects=False,
        )
        assert response.status_code == 409
        assert "capacidad" in response.text.lower() or "plan cambió" in response.text.lower()

    with SessionLocal() as session:
        invitation = session.scalar(select(UserInvitation).where(UserInvitation.email == "reserva@empresa.co"))
        user = session.scalar(select(AppUser).where(AppUser.email == "reserva@empresa.co"))
        assert invitation is not None and invitation.status == "Pendiente"
        assert user is None


def test_v056_service_operation_is_restricted_to_subscription_managers():
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        assert client.get("/operacion-servicio").status_code == 403
        assert client.get("/api/operacion-servicio/resumen").status_code == 403
