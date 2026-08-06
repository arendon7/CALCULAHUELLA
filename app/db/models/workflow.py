from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class WorkItem(Base):
    """Universal unit of accountable work across the carbon-management lifecycle.

    The model is additive. Existing DataRequest, ReviewObservation, PeriodClose and
    related records remain authoritative until their flows are migrated explicitly.
    """

    __tablename__ = "work_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    stage_code: Mapped[str] = mapped_column(String(40), default="collect", index=True)
    work_type: Mapped[str] = mapped_column(String(60), default="data_request", index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    status_code: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)

    requester_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id"), nullable=True)
    requester_email: Mapped[str] = mapped_column(String(180), default="")
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id"), nullable=True)
    assignee_email: Mapped[str] = mapped_column(String(180), default="", index=True)
    assignee_role: Mapped[str] = mapped_column(String(60), default="")
    assignee_area: Mapped[str] = mapped_column(String(120), default="")

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    blocking_reason: Mapped[str] = mapped_column(Text, default="")

    source_entity_type: Mapped[str] = mapped_column(String(80), default="")
    source_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_route: Mapped[str] = mapped_column(String(260), default="")

    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    events: Mapped[list["WorkItemEvent"]] = relationship(
        back_populates="work_item",
        cascade="all, delete-orphan",
        order_by="WorkItemEvent.id",
    )
    links: Mapped[list["WorkItemLink"]] = relationship(
        back_populates="work_item",
        cascade="all, delete-orphan",
        order_by="WorkItemLink.id",
    )
    dependencies: Mapped[list["WorkItemDependency"]] = relationship(
        foreign_keys="WorkItemDependency.work_item_id",
        back_populates="work_item",
        cascade="all, delete-orphan",
    )


class WorkItemEvent(Base):
    __tablename__ = "work_item_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    event_code: Mapped[str] = mapped_column(String(60), index=True)
    from_status_code: Mapped[str] = mapped_column(String(40), default="")
    to_status_code: Mapped[str] = mapped_column(String(40), default="")
    actor_email: Mapped[str] = mapped_column(String(180), default="")
    actor_role: Mapped[str] = mapped_column(String(60), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)

    work_item: Mapped[WorkItem] = relationship(back_populates="events")


class WorkItemLink(Base):
    __tablename__ = "work_item_links"
    __table_args__ = (
        UniqueConstraint(
            "work_item_id",
            "entity_type",
            "entity_id",
            "relationship_type",
            name="uq_work_item_link_entity_relation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(60), default="related")
    label: Mapped[str] = mapped_column(String(180), default="")
    route: Mapped[str] = mapped_column(String(260), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    work_item: Mapped[WorkItem] = relationship(back_populates="links")


class WorkItemDependency(Base):
    __tablename__ = "work_item_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "work_item_id",
            "depends_on_work_item_id",
            name="uq_work_item_dependency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    depends_on_work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), index=True)
    dependency_type: Mapped[str] = mapped_column(String(40), default="finish_to_start")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    work_item: Mapped[WorkItem] = relationship(
        foreign_keys=[work_item_id],
        back_populates="dependencies",
    )
    depends_on: Mapped[WorkItem] = relationship(foreign_keys=[depends_on_work_item_id])
