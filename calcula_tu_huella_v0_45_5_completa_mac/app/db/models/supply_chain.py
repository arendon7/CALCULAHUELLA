from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(180))
    tax_id: Mapped[str] = mapped_column(String(40), default="")
    sector: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(80), default="Colombia")
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    contact_email: Mapped[str] = mapped_column(String(180), default="")
    annual_spend_cop: Mapped[float] = mapped_column(Float, default=0)
    strategic: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(30), default="Medio")
    status: Mapped[str] = mapped_column(String(30), default="Activo")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship(back_populates="suppliers")
    requests: Mapped[list["SupplierDataRequest"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")

class SupplierCampaign(Base):
    __tablename__ = "supplier_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(150), default="Bienes y servicios adquiridos")
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    methodology: Mapped[str] = mapped_column(String(180), default="GHG Protocol Scope 3")
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="supplier_campaigns")
    requests: Mapped[list["SupplierDataRequest"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")

class SupplierDataRequest(Base):
    __tablename__ = "supplier_data_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("supplier_campaigns.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_service: Mapped[str] = mapped_column(String(180))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(40), default="unidad")
    spend_cop: Mapped[float] = mapped_column(Float, default=0)
    requested_method: Mapped[str] = mapped_column(String(120), default="Factor específico del proveedor")
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    due_date: Mapped[date] = mapped_column(Date)
    access_token: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    campaign: Mapped[SupplierCampaign] = relationship(back_populates="requests")
    supplier: Mapped[Supplier] = relationship(back_populates="requests")
    response: Mapped["SupplierResponse | None"] = relationship(back_populates="request", cascade="all, delete-orphan", uselist=False)

class SupplierResponse(Base):
    __tablename__ = "supplier_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("supplier_data_requests.id"), unique=True)
    method: Mapped[str] = mapped_column(String(100), default="Factor por unidad")
    activity_value: Mapped[float] = mapped_column(Float, default=0)
    activity_unit: Mapped[str] = mapped_column(String(40), default="")
    emission_factor: Mapped[float] = mapped_column(Float, default=0)
    factor_unit: Mapped[str] = mapped_column(String(100), default="kg CO2e/unidad")
    reported_emissions_tco2e: Mapped[float] = mapped_column(Float, default=0)
    calculated_emissions_tco2e: Mapped[float] = mapped_column(Float, default=0)
    methodology: Mapped[str] = mapped_column(String(220), default="")
    boundary: Mapped[str] = mapped_column(String(220), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_level: Mapped[str] = mapped_column(String(20), default="C")
    evidence_name: Mapped[str] = mapped_column(String(180), default="")
    evidence_stored_name: Mapped[str] = mapped_column(String(240), default="")
    evidence_sha256: Mapped[str] = mapped_column(String(64), default="")
    evidence_size: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    reviewer_comments: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")

    request: Mapped[SupplierDataRequest] = relationship(back_populates="response")
