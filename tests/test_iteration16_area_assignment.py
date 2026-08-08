from __future__ import annotations

import pytest
from sqlalchemy import select

from app.access_control import ROLE_CAPABILITIES
from app.database import AppUser, OrganizationMembership, SessionLocal
from app.main import app  # noqa: F401 - loads workflow bridge and route registration
from app.workflow_service import create_work_item

pytestmark = pytest.mark.smoke


def test_iteration16_area_only_assignment_defaults_to_client_role() -> None:
    with SessionLocal() as session:
        membership = session.scalar(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.role == "Administrador",
                OrganizationMembership.active.is_(True),
            )
            .order_by(OrganizationMembership.id)
        )
        assert membership is not None
        db_user = session.get(AppUser, membership.user_id)
        assert db_user is not None
        admin = {
            "id": db_user.id,
            "organization_id": membership.organization_id,
            "email": db_user.email,
            "role": membership.role,
            "capabilities": ROLE_CAPABILITIES[membership.role],
        }
        item = create_work_item(
            session,
            admin,
            title="Entregar soportes de combustible",
            work_type="evidence_request",
            assignee_area="Contabilidad",
            acceptance_criteria="Facturas legibles, periodo identificado y fuente relacionada.",
        )
        session.flush()
        assert item.assignee_area == "Contabilidad"
        assert item.assignee_role == "Cliente"
