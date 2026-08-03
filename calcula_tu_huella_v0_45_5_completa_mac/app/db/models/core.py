from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True)
    trade_name: Mapped[str] = mapped_column(String(180), default="")
    tax_id: Mapped[str] = mapped_column(String(30))
    sector: Mapped[str] = mapped_column(String(100))
    ciiu_code: Mapped[str] = mapped_column(String(20), default="")
    country: Mapped[str] = mapped_column(String(80), default="Colombia")
    department: Mapped[str] = mapped_column(String(80), default="Antioquia")
    city: Mapped[str] = mapped_column(String(100))
    employees: Mapped[int] = mapped_column(Integer, default=0)
    annual_revenue: Mapped[float] = mapped_column(Float, default=0)
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    contact_email: Mapped[str] = mapped_column(String(150), default="")
    status: Mapped[str] = mapped_column(String(30), default="Activa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    facilities: Mapped[list["Facility"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    inventories: Mapped[list["Inventory"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    users: Mapped[list["AppUser"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    suppliers: Mapped[list["Supplier"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    platform_settings: Mapped[list["PlatformSetting"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    automations: Mapped[list["ScheduledAutomation"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    integrations: Mapped[list["IntegrationConnection"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="users")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_preference: Mapped["NotificationPreference | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    memberships: Mapped[list["OrganizationMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), default="Cliente")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    user: Mapped[AppUser] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")

class PlatformSetting(Base):
    __tablename__ = "platform_settings"
    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_platform_setting_org_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text, default="")
    value_type: Mapped[str] = mapped_column(String(30), default="text")
    description: Mapped[str] = mapped_column(String(240), default="")
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship(back_populates="platform_settings")

class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(150))
    facility_type: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(220), default="")
    employees: Mapped[int] = mapped_column(Integer, default=0)
    operational_control: Mapped[bool] = mapped_column(Boolean, default=True)
    financial_control: Mapped[bool] = mapped_column(Boolean, default=True)
    ownership_percentage: Mapped[float] = mapped_column(Float, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped[Organization] = relationship(back_populates="facilities")
    source_records: Mapped[list["EmissionSource"]] = relationship(back_populates="facility")
    inventory_links: Mapped[list["InventoryFacility"]] = relationship(back_populates="facility", cascade="all, delete-orphan")
    activity_indicators: Mapped[list["ActivityIndicator"]] = relationship(back_populates="facility")
