from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class LandCarbonEntry(Base):
    __tablename__ = "land_carbon_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(50))
    activity_name: Mapped[str] = mapped_column(String(180))
    land_category: Mapped[str] = mapped_column(String(100), default="No aplica")
    carbon_pool: Mapped[str] = mapped_column(String(100), default="No aplica")
    location: Mapped[str] = mapped_column(String(160), default="")
    reporting_scope: Mapped[str] = mapped_column(String(30), default="Fuera de alcances")
    gas: Mapped[str] = mapped_column(String(30), default="CO2")
    quantity_tco2e: Mapped[float] = mapped_column(Float, default=0)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    methodology: Mapped[str] = mapped_column(String(220), default="")
    source_reference: Mapped[str] = mapped_column(String(300), default="")
    traceability_level: Mapped[str] = mapped_column(String(40), default="País de origen")
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    storage_duration_years: Mapped[int] = mapped_column(Integer, default=0)
    reversal_monitoring: Mapped[bool] = mapped_column(Boolean, default=False)
    additionality_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    lifecycle_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inventory: Mapped["Inventory"] = relationship(back_populates="land_carbon_entries")
