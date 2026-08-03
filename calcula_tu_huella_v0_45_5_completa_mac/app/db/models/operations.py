from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class ScheduledAutomation(Base):
    __tablename__ = "scheduled_automations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    automation_type: Mapped[str] = mapped_column(String(80))
    cadence: Mapped[str] = mapped_column(String(30), default="Semanal")
    schedule_time: Mapped[str] = mapped_column(String(10), default="08:00")
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), default="America/Bogota")
    recipient_roles: Mapped[str] = mapped_column(Text, default='["Administrador", "Consultor"]')
    days_before: Mapped[int] = mapped_column(Integer, default=3)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship(back_populates="automations")
    inventory: Mapped["Inventory | None"] = relationship()
    runs: Mapped[list["AutomationRun"]] = relationship(back_populates="automation", cascade="all, delete-orphan")

class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    automation_id: Mapped[int] = mapped_column(ForeignKey("scheduled_automations.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="Ejecutado")
    summary: Mapped[str] = mapped_column(Text, default="")
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    automation: Mapped[ScheduledAutomation] = relationship(back_populates="runs")

class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    provider: Mapped[str] = mapped_column(String(80), default="API REST")
    integration_type: Mapped[str] = mapped_column(String(80), default="Entrada de datos")
    status: Mapped[str] = mapped_column(String(40), default="Configurada")
    endpoint_url: Mapped[str] = mapped_column(String(300), default="")
    api_key_hash: Mapped[str] = mapped_column(String(128), default="")
    api_key_prefix: Mapped[str] = mapped_column(String(20), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_detail: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship(back_populates="integrations")
    events: Mapped[list["IntegrationEvent"]] = relationship(back_populates="integration", cascade="all, delete-orphan")

class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integration_connections.id"), index=True)
    activity_data_id: Mapped[int | None] = mapped_column(ForeignKey("activity_data.id"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), default="Entrada")
    event_type: Mapped[str] = mapped_column(String(80), default="Dato de actividad")
    status: Mapped[str] = mapped_column(String(30), default="Recibido")
    detail: Mapped[str] = mapped_column(Text, default="")
    external_reference: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    integration: Mapped[IntegrationConnection] = relationship(back_populates="events")

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), unique=True, index=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    digest_frequency: Mapped[str] = mapped_column(String(30), default="Inmediato")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user: Mapped[AppUser] = relationship(back_populates="notification_preference")

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(300), default="")
    category: Mapped[str] = mapped_column(String(60), default="Sistema")
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="Entregada")
    email_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    delivery_detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="notifications")
    user: Mapped[AppUser | None] = relationship(back_populates="notifications")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    user_email: Mapped[str] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_label: Mapped[str] = mapped_column(String(180))
    detail: Mapped[str] = mapped_column(Text, default="")
    previous_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    request_id: Mapped[str] = mapped_column(String(80), default="")
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class RestoreDrill(Base):
    __tablename__ = "restore_drills"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    backup_name: Mapped[str] = mapped_column(String(240), index=True)
    backup_sha256: Mapped[str] = mapped_column(String(64), default="")
    application_version: Mapped[str] = mapped_column(String(30), default="")
    database_backend: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(30), default="En ejecución", index=True)
    integrity_result: Mapped[str] = mapped_column(String(80), default="")
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    record_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    checks_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(180), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

class LoginSecurityState(Base):
    __tablename__ = "login_security_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class DeploymentRehearsal(Base):
    __tablename__ = "deployment_rehearsals"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="En ejecución", index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    strict_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String(30), default="local")
    database_backend: Mapped[str] = mapped_column(String(40), default="")
    storage_backend: Mapped[str] = mapped_column(String(40), default="")
    checks_json: Mapped[str] = mapped_column(Text, default="[]")
    blockers_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(180), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class ReleaseCertification(Base):
    __tablename__ = "release_certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    application_version: Mapped[str] = mapped_column(String(30), index=True)
    scope: Mapped[str] = mapped_column(String(30), default="Local", index=True)
    status: Mapped[str] = mapped_column(String(40), default="En ejecución", index=True)
    production_approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    certificate_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    artifact_name: Mapped[str] = mapped_column(String(240), default="")
    artifact_sha256: Mapped[str] = mapped_column(String(64), default="")
    external_artifact_key: Mapped[str] = mapped_column(String(400), default="")
    backup_name: Mapped[str] = mapped_column(String(240), default="")
    backup_sha256: Mapped[str] = mapped_column(String(64), default="")
    external_backup_key: Mapped[str] = mapped_column(String(400), default="")
    restore_drill_id: Mapped[int | None] = mapped_column(ForeignKey("restore_drills.id"), nullable=True, index=True)
    deployment_rehearsal_id: Mapped[int | None] = mapped_column(ForeignKey("deployment_rehearsals.id"), nullable=True, index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    blockers_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(180), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class DemoEnvironmentCertification(Base):
    __tablename__ = "demo_environment_certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    application_version: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(40), default="En ejecución", index=True)
    certificate_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    artifact_name: Mapped[str] = mapped_column(String(240), default="")
    artifact_sha256: Mapped[str] = mapped_column(String(64), default="")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    checks_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    performed_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))



class OperationalIncident(Base):
    __tablename__ = "operational_incidents"
    __table_args__ = (UniqueConstraint("organization_id", "fingerprint", name="uq_operational_incident_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(220))
    severity: Mapped[str] = mapped_column(String(30), default="Media", index=True)
    status: Mapped[str] = mapped_column(String(30), default="Abierto", index=True)
    source: Mapped[str] = mapped_column(String(80), default="Puerta productiva")
    detail: Mapped[str] = mapped_column(Text, default="")
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    acknowledged_by: Mapped[str] = mapped_column(String(180), default="")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(180), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
