from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .access_control import ROLE_CAPABILITIES
from .database import AppUser, Organization, OrganizationMembership, SessionLocal
from .product_experience import normalize_view_mode, role_profile


def _active_memberships(session: Session, db_user: AppUser) -> list[OrganizationMembership]:
    memberships = list(
        session.scalars(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == db_user.id,
                OrganizationMembership.active.is_(True),
            )
            .options(selectinload(OrganizationMembership.organization))
            .order_by(OrganizationMembership.id)
        )
    )
    if memberships:
        return memberships

    membership = OrganizationMembership(
        user_id=db_user.id,
        organization_id=db_user.organization_id,
        role=db_user.role,
        active=True,
    )
    session.add(membership)
    session.commit()
    session.refresh(membership)
    membership.organization = session.get(Organization, membership.organization_id)
    return [membership]


def _active_membership(
    request: Request,
    memberships: list[OrganizationMembership],
    primary_organization_id: int,
) -> OrganizationMembership:
    requested_org = request.session.get("active_org_id")
    active = next(
        (item for item in memberships if item.organization_id == requested_org),
        None,
    )
    if active:
        return active

    active = next(
        (item for item in memberships if item.organization_id == primary_organization_id),
        memberships[0],
    )
    request.session["active_org_id"] = active.organization_id
    return active


def _capability_flags(capabilities: set[str]) -> dict[str, bool]:
    return {
        "can_manage_org": "manage_org" in capabilities,
        "can_manage_inventory": "manage_inventory" in capabilities,
        "can_manage_sources": "manage_sources" in capabilities,
        "can_review": "review" in capabilities,
        "can_approve": "approve" in capabilities,
        "can_provide_data": "provide_data" in capabilities or "manage_sources" in capabilities,
        "can_view_methodology": "view_methodology" in capabilities,
        "can_external_audit": "external_audit" in capabilities,
        "can_manage_supply_chain": "manage_supply_chain" in capabilities,
        "can_manage_operations": "manage_operations" in capabilities,
        "can_manage_automations": "manage_automations" in capabilities,
        "can_manage_integrations": "manage_integrations" in capabilities,
        "can_manage_portfolio": "manage_portfolio" in capabilities,
        "can_manage_compliance": "manage_compliance" in capabilities,
        "can_view_compliance": "view_compliance" in capabilities or "manage_compliance" in capabilities,
        "can_manage_documents": "manage_documents" in capabilities,
        "can_manage_methodology_governance": "manage_methodology_governance" in capabilities,
        "can_manage_readiness": "manage_readiness" in capabilities,
        "can_manage_subscription": "manage_subscription" in capabilities,
        "can_manage_support": "manage_support" in capabilities,
        "can_manage_saas": "manage_saas" in capabilities,
        "can_manage_commercial": "manage_commercial" in capabilities,
        "can_manage_customer_success": "manage_customer_success" in capabilities,
        "can_view_customer_success": "view_customer_success" in capabilities or "manage_customer_success" in capabilities,
        "can_manage_impact": "manage_impact" in capabilities,
        "can_view_impact": "view_impact" in capabilities or "manage_impact" in capabilities,
        "can_manage_climate_risk": "manage_climate_risk" in capabilities,
        "can_view_climate_risk": "view_climate_risk" in capabilities or "manage_climate_risk" in capabilities,
        "can_manage_climate_disclosure": "manage_climate_disclosure" in capabilities,
        "can_view_climate_disclosure": "view_climate_disclosure" in capabilities or "manage_climate_disclosure" in capabilities,
        "can_manage_consolidation": "manage_consolidation" in capabilities,
        "can_view_consolidation": "view_consolidation" in capabilities or "manage_consolidation" in capabilities,
    }


def resolve_current_user(request: Request) -> dict[str, object] | None:
    email = request.session.get("user_email")
    if not email:
        return None

    with SessionLocal() as session:
        db_user = session.scalar(
            select(AppUser).where(
                AppUser.email == email,
                AppUser.active.is_(True),
            )
        )
        if not db_user:
            return None

        memberships = _active_memberships(session, db_user)
        active_membership = _active_membership(
            request,
            memberships,
            db_user.organization_id,
        )
        role = active_membership.role
        capabilities = ROLE_CAPABILITIES.get(role, set())
        view_mode = normalize_view_mode(request.session.get("view_mode"))
        initials = "".join(piece[0] for piece in db_user.name.split()[:2]).upper()
        organization_options = [
            {
                "id": item.organization_id,
                "name": item.organization.name,
                "trade_name": item.organization.trade_name,
                "role": item.role,
            }
            for item in memberships
            if item.organization
        ]
        user = {
            "id": db_user.id,
            "organization_id": active_membership.organization_id,
            "primary_organization_id": db_user.organization_id,
            "email": db_user.email,
            "role": role,
            "name": db_user.name,
            "initials": initials,
            "organizations": organization_options,
            "capabilities": capabilities,
            "view_mode": view_mode,
            "profile": role_profile(role),
        }
        user.update(_capability_flags(capabilities))
        return user
