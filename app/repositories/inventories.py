from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import Inventory


def list_inventories(session: Session, organization_id: int) -> list[Inventory]:
    return list(
        session.scalars(
            select(Inventory)
            .where(Inventory.organization_id == organization_id)
            .options(selectinload(Inventory.sources), selectinload(Inventory.facility_links))
            .order_by(Inventory.start_date.desc())
        )
    )


def get_inventory(session: Session, organization_id: int, inventory_id: int) -> Inventory | None:
    return session.scalar(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.organization_id == organization_id,
        )
    )
