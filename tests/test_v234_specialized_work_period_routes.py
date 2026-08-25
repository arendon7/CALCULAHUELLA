from __future__ import annotations

import inspect

from sqlalchemy import select

from app.database import AppUser, Inventory, SessionLocal, WorkItemLink
from app.workflow_integrations import (
    WorkSourceSpec,
    _inventory_route,
    _sync_period_closes,
    _sync_reduction_actions,
    _sync_reports,
    _sync_review_observations,
    _upsert,
)


def test_v234_upsert_repairs_stale_specialized_item_and_origin_link_routes() -> None:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == "consultor@calculatuhuella.local"))
        assert user is not None
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.organization_id == user.organization_id)
            .order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        assert inventory is not None
        expected_route = _inventory_route(inventory.id)
        spec = WorkSourceSpec(
            entity_type="ReviewObservation",
            entity_id=9_900_234,
            organization_id=user.organization_id,
            inventory_id=inventory.id,
            work_type="inventory_review",
            title="V2.34 · prueba de origen especializado",
            description="Prueba transaccional de reparación de contexto.",
            status_code="assigned",
            priority="normal",
            assignee_email="",
            assignee_role="Revisor",
            assignee_area="",
            due_date=None,
            acceptance_criteria="Conservar el expediente explícito del periodo.",
            next_action="Revisar el expediente.",
            source_route=expected_route,
        )
        item, created = _upsert(session, spec, user.email)
        session.flush()
        assert created is True
        origin = session.scalar(
            select(WorkItemLink).where(
                WorkItemLink.work_item_id == item.id,
                WorkItemLink.relationship_type == "origin",
            )
        )
        assert origin is not None

        item.source_route = "/control"
        origin.route = "/control"
        session.flush()

        repaired, changed = _upsert(session, spec, user.email)
        session.flush()
        assert changed is True
        assert repaired.source_route == expected_route
        repaired_origin = session.scalar(
            select(WorkItemLink).where(
                WorkItemLink.work_item_id == repaired.id,
                WorkItemLink.relationship_type == "origin",
            )
        )
        assert repaired_origin is not None
        assert repaired_origin.route == expected_route
        session.rollback()


def test_v234_inventory_bound_specialized_producers_do_not_use_generic_default_routes() -> None:
    contracts = {
        _sync_review_observations: 'source_route=_inventory_route(record.inventory_id)',
        _sync_period_closes: 'source_route=_inventory_route(record.inventory_id)',
        _sync_reports: 'source_route=_inventory_route(record.inventory_id)',
        _sync_reduction_actions: 'source_route=_inventory_route(record.inventory_id)',
    }
    forbidden = {
        _sync_review_observations: 'source_route="/control"',
        _sync_period_closes: 'source_route="/cierre-mensual"',
        _sync_reports: 'source_route="/reportes"',
        _sync_reduction_actions: 'source_route="/reduccion"',
    }
    for producer, expected in contracts.items():
        source = inspect.getsource(producer)
        assert expected in source
        assert forbidden[producer] not in source
