from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import Facility, Organization


def get_organization(session: Session, organization_id: int, *, include_graph: bool = False) -> Organization | None:
    statement = select(Organization).where(Organization.id == organization_id)
    if include_graph:
        statement = statement.options(
            selectinload(Organization.facilities),
            selectinload(Organization.users),
            selectinload(Organization.inventories),
        )
    return session.scalar(statement)


def list_active_facilities(session: Session, organization_id: int) -> list[Facility]:
    return list(
        session.scalars(
            select(Facility)
            .where(Facility.organization_id == organization_id, Facility.active.is_(True))
            .order_by(Facility.name)
        )
    )


def get_facility(session: Session, organization_id: int, facility_id: int) -> Facility | None:
    return session.scalar(
        select(Facility).where(
            Facility.id == facility_id,
            Facility.organization_id == organization_id,
        )
    )


def list_facilities_by_ids(session: Session, organization_id: int, facility_ids: list[int]) -> list[Facility]:
    if not facility_ids:
        return []
    return list(
        session.scalars(
            select(Facility).where(
                Facility.organization_id == organization_id,
                Facility.id.in_(facility_ids),
            )
        )
    )
