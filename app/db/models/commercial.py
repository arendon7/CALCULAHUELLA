from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


MONEY_TYPE = Numeric(18, 2, asdecimal=True)
RATE_TYPE = Numeric(9, 6, asdecimal=True)
RECURRING_BASIS_TYPE = Numeric(18, 6, asdecimal=True)
ZERO_MONEY = Decimal("0.00")
ZERO_RATE = Decimal("0.000000")


class CommercialReadinessItem(Base):
    __tablename__ = "commercial_readiness_items"
    __table_args__ = (UniqueConstraint("organization_id", "category", "title", name="uq_readiness_org_category_title"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    owner: Mapped[str] = mapped_column(String(140), default="Equipo fundador")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()


class ServicePlan(Base):
    __tablename__ = "service_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    monthly_fee: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    annual_fee: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    max_users: Mapped[int] = mapped_column(Integer, default=5)
    max_facilities: Mapped[int] = mapped_column(Integer, default=3)
    max_inventories: Mapped[int] = mapped_column(Integer, default=3)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=1024)
    includes_scope3: Mapped[bool] = mapped_column(Boolean, default=False)
    includes_verification_portal: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class OrganizationSubscription(Base):
    __tablename__ = "organization_subscriptions"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_subscription_organization"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("service_plans.id"), index=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="Anual")
    status: Mapped[str] = mapped_column(String(30), default="Prueba")
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    trial_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    custom_monthly_fee: Mapped[Decimal | None] = mapped_column(RECURRING_BASIS_TYPE, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    plan: Mapped[ServicePlan] = relationship()


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("organization_id", "metric", "period_start", name="uq_usage_org_metric_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(80), default="Sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class CustomerOnboardingItem(Base):
    __tablename__ = "customer_onboarding_items"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_onboarding_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    owner: Mapped[str] = mapped_column(String(140), default="Cliente")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True, index=True)
    activity_data_id: Mapped[int | None] = mapped_column(ForeignKey("activity_data.id"), nullable=True, index=True)
    public_reference: Mapped[str] = mapped_column(String(40), default="", index=True)
    created_by: Mapped[str] = mapped_column(String(180))
    request_type: Mapped[str] = mapped_column(String(60), default="Consulta")
    category: Mapped[str] = mapped_column(String(80), default="Soporte funcional")
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="Abierto")
    subject: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    desired_outcome: Mapped[str] = mapped_column(Text, default="")
    assigned_to: Mapped[str] = mapped_column(String(180), default="Equipo de soporte")
    resolution: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped[Organization] = relationship()
    inventory: Mapped["Inventory | None"] = relationship()
    source: Mapped["EmissionSource | None"] = relationship()
    activity_data: Mapped["ActivityData | None"] = relationship()
    messages: Mapped[list["SupportMessage"]] = relationship(back_populates="ticket", cascade="all, delete-orphan", order_by="SupportMessage.created_at")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), index=True)
    author_email: Mapped[str] = mapped_column(String(180))
    author_role: Mapped[str] = mapped_column(String(40), default="Cliente")
    message_type: Mapped[str] = mapped_column(String(50), default="Mensaje")
    body: Mapped[str] = mapped_column(Text)
    visible_to_client: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")


class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(180), index=True)
    invited_name: Mapped[str] = mapped_column(String(140), default="")
    role: Mapped[str] = mapped_column(String(40), default="Cliente")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente", index=True)
    invited_by: Mapped[str] = mapped_column(String(180), default="sistema")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("organization_subscriptions.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    issued_at: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    subscription: Mapped[OrganizationSubscription | None] = relationship()


class CommercialLead(Base):
    __tablename__ = "commercial_leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(180))
    contact_name: Mapped[str] = mapped_column(String(140))
    email: Mapped[str] = mapped_column(String(180), index=True)
    phone: Mapped[str] = mapped_column(String(60), default="")
    sector: Mapped[str] = mapped_column(String(100), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    employees_band: Mapped[str] = mapped_column(String(60), default="")
    facilities_count: Mapped[int] = mapped_column(Integer, default=1)
    has_previous_inventory: Mapped[bool] = mapped_column(Boolean, default=False)
    desired_scopes: Mapped[str] = mapped_column(String(80), default="Alcances 1 y 2")
    objective: Mapped[str] = mapped_column(String(160), default="Conocer la huella corporativa")
    urgency: Mapped[str] = mapped_column(String(40), default="Normal")
    notes: Mapped[str] = mapped_column(Text, default="")
    complexity_score: Mapped[int] = mapped_column(Integer, default=0)
    recommended_plan_code: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(30), default="Nuevo")
    assigned_to: Mapped[str] = mapped_column(String(180), default="Equipo comercial")
    source: Mapped[str] = mapped_column(String(80), default="Sitio web")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class CommercialProposal(Base):
    __tablename__ = "commercial_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("commercial_leads.id"), nullable=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("service_plans.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    public_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    company_name: Mapped[str] = mapped_column(String(180))
    contact_name: Mapped[str] = mapped_column(String(140), default="")
    contact_email: Mapped[str] = mapped_column(String(180), default="")
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="Anual")
    implementation_fee: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    recurring_fee: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    discount_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    tax_rate: Mapped[Decimal] = mapped_column(RATE_TYPE, default=ZERO_RATE)
    first_year_total: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    scope_json: Mapped[str] = mapped_column(Text, default="[]")
    deliverables_json: Mapped[str] = mapped_column(Text, default="[]")
    terms: Mapped[str] = mapped_column(Text, default="")
    contract_version: Mapped[str] = mapped_column(String(30), default="1.0")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_by: Mapped[str] = mapped_column(String(180), default="")
    accepted_email: Mapped[str] = mapped_column(String(180), default="")
    accepted_ip: Mapped[str] = mapped_column(String(80), default="")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acceptance_hash: Mapped[str] = mapped_column(String(64), default="")
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    lead: Mapped[CommercialLead | None] = relationship()
    organization: Mapped[Organization | None] = relationship()
    plan: Mapped[ServicePlan | None] = relationship()


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("commercial_proposals.id"), nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("billing_invoices.id"), nullable=True, index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("organization_subscriptions.id"), nullable=True, index=True)
    public_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    gateway: Mapped[str] = mapped_column(String(40), default="Demo")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    currency: Mapped[str] = mapped_column(String(10), default="COP")
    external_reference: Mapped[str] = mapped_column(String(120), default="")
    payer_name: Mapped[str] = mapped_column(String(180), default="")
    payer_email: Mapped[str] = mapped_column(String(180), default="")
    provider_payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    proposal: Mapped[CommercialProposal | None] = relationship()
    invoice: Mapped[BillingInvoice | None] = relationship()
    subscription: Mapped[OrganizationSubscription | None] = relationship()


class ServiceContract(Base):
    __tablename__ = "service_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("commercial_proposals.id"), nullable=True, index=True)
    parent_contract_id: Mapped[int | None] = mapped_column(ForeignKey("service_contracts.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    version: Mapped[str] = mapped_column(String(30), default="1.0")
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_type: Mapped[str] = mapped_column(String(40), default="Anual")
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    notice_days: Mapped[int] = mapped_column(Integer, default=30)
    contract_value: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="Anual")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo comercial")
    terms_snapshot: Mapped[str] = mapped_column(Text, default="")
    signed_by: Mapped[str] = mapped_column(String(180), default="")
    signed_email: Mapped[str] = mapped_column(String(180), default="")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signature_hash: Mapped[str] = mapped_column(String(64), default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    proposal: Mapped[CommercialProposal | None] = relationship()
    parent_contract: Mapped["ServiceContract | None"] = relationship(remote_side="ServiceContract.id")


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("service_contracts.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    service_type: Mapped[str] = mapped_column(String(100), default="Implementación")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Planeada")
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(180), default="Equipo de implementación")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    contract: Mapped[ServiceContract | None] = relationship()


class CollectionAction(Base):
    __tablename__ = "collection_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(80), default="Recordatorio")
    channel: Mapped[str] = mapped_column(String(50), default="Correo")
    recipient: Mapped[str] = mapped_column(String(180), default="")
    due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    notes: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    invoice: Mapped[BillingInvoice] = relationship()


class BillingDocumentRecord(Base):
    __tablename__ = "billing_document_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("billing_invoices.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(80), default="Documento de cobro interno")
    internal_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(100), default="Sin integración")
    external_number: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(40), default="Pendiente de integración")
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    cufe: Mapped[str] = mapped_column(String(180), default="")
    document_url: Mapped[str] = mapped_column(String(400), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    invoice: Mapped[BillingInvoice] = relationship()


class CustomerSuccessProfile(Base):
    __tablename__ = "customer_success_profiles"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_customer_success_profile_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(40), default="Implementación")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo de éxito del cliente")
    executive_sponsor: Mapped[str] = mapped_column(String(180), default="")
    sponsor_email: Mapped[str] = mapped_column(String(180), default="")
    primary_objective: Mapped[str] = mapped_column(Text, default="")
    success_plan: Mapped[str] = mapped_column(Text, default="")
    risk_override: Mapped[str] = mapped_column(String(30), default="")
    risk_reason: Mapped[str] = mapped_column(Text, default="")
    last_business_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_business_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    satisfaction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()


class AccountHealthSnapshot(Base):
    __tablename__ = "account_health_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    adoption_score: Mapped[int] = mapped_column(Integer, default=0)
    delivery_score: Mapped[int] = mapped_column(Integer, default=0)
    support_score: Mapped[int] = mapped_column(Integer, default=0)
    commercial_score: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(30), default="Atención")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")

    organization: Mapped[Organization] = relationship()


class ValueMilestone(Base):
    __tablename__ = "value_milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    category: Mapped[str] = mapped_column(String(80), default="Resultado climático")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo de éxito del cliente")
    status: Mapped[str] = mapped_column(String(30), default="Planeado")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_value: Mapped[float] = mapped_column(Float, default=0)
    realized_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(60), default="")
    evidence_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped["Inventory | None"] = relationship()


class SuccessCommitment(Base):
    __tablename__ = "success_commitments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo de éxito del cliente")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    source: Mapped[str] = mapped_column(String(80), default="Plan de éxito")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()


class RenewalOpportunity(Base):
    __tablename__ = "renewal_opportunities"
    __table_args__ = (UniqueConstraint("contract_id", name="uq_renewal_contract"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("service_contracts.id"), nullable=True, index=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="Por preparar")
    probability: Mapped[int] = mapped_column(Integer, default=50)
    forecast_amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, default=ZERO_MONEY)
    strategy: Mapped[str] = mapped_column(Text, default="")
    blockers: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_notes: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    contract: Mapped["ServiceContract | None"] = relationship()
