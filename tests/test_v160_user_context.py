from __future__ import annotations

from sqlalchemy import select
from starlette.requests import Request

from app.access_control import ROLE_CAPABILITIES
from app.database import AppUser, Organization, OrganizationMembership, SessionLocal
from app.user_context import resolve_current_user


def _request(session_values: dict[str, object]) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "session": session_values,
        }
    )


def test_user_context_returns_none_without_authenticated_session() -> None:
    assert resolve_current_user(_request({})) is None


def test_user_context_resolves_primary_membership_and_capabilities() -> None:
    request = _request({"user_email": "admin@calculatuhuella.local"})
    user = resolve_current_user(request)
    assert user is not None
    assert request.session["active_org_id"] == user["organization_id"]
    assert user["capabilities"] == ROLE_CAPABILITIES[user["role"]]
    assert user["can_manage_org"] == ("manage_org" in user["capabilities"])
    assert user["can_provide_data"] == (
        "provide_data" in user["capabilities"] or "manage_sources" in user["capabilities"]
    )


def test_user_context_uses_role_from_active_organization_membership() -> None:
    with SessionLocal() as session:
        db_user = session.scalar(
            select(AppUser).where(AppUser.email == "admin@calculatuhuella.local")
        )
        assert db_user is not None
        extra = Organization(
            name="Organización B3 contexto",
            trade_name="B3",
            tax_id="B3-CTX-001",
            sector="Servicios y oficinas",
            city="Medellín",
        )
        session.add(extra)
        session.flush()
        session.add(
            OrganizationMembership(
                user_id=db_user.id,
                organization_id=extra.id,
                role="Cliente",
                active=True,
            )
        )
        session.commit()
        extra_id = extra.id

    request = _request(
        {
            "user_email": "admin@calculatuhuella.local",
            "active_org_id": extra_id,
        }
    )
    user = resolve_current_user(request)
    assert user is not None
    assert user["organization_id"] == extra_id
    assert user["role"] == "Cliente"
    assert user["capabilities"] == ROLE_CAPABILITIES["Cliente"]
    assert user["can_manage_org"] is False
    assert any(item["id"] == extra_id and item["role"] == "Cliente" for item in user["organizations"])


def test_user_context_rejects_unavailable_active_org_and_restores_primary() -> None:
    request = _request(
        {
            "user_email": "admin@calculatuhuella.local",
            "active_org_id": 999999999,
        }
    )
    user = resolve_current_user(request)
    assert user is not None
    assert user["organization_id"] == user["primary_organization_id"]
    assert request.session["active_org_id"] == user["primary_organization_id"]
