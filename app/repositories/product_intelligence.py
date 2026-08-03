from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import (
    DiagnosticAssessment,
    ImplementationPlan,
    OrganizationCarbonProfile,
)


def get_carbon_profile(session: Session, organization_id: int) -> OrganizationCarbonProfile | None:
    return session.scalar(
        select(OrganizationCarbonProfile).where(
            OrganizationCarbonProfile.organization_id == organization_id
        )
    )


def get_or_create_carbon_profile(session: Session, organization_id: int) -> OrganizationCarbonProfile:
    profile = get_carbon_profile(session, organization_id)
    if profile:
        return profile
    profile = OrganizationCarbonProfile(organization_id=organization_id)
    session.add(profile)
    session.flush()
    return profile


def list_assessments(session: Session, organization_id: int) -> list[DiagnosticAssessment]:
    return list(
        session.scalars(
            select(DiagnosticAssessment)
            .where(DiagnosticAssessment.organization_id == organization_id)
            .order_by(DiagnosticAssessment.assessed_at.desc(), DiagnosticAssessment.id.desc())
        )
    )


def latest_assessment(session: Session, organization_id: int) -> DiagnosticAssessment | None:
    return session.scalar(
        select(DiagnosticAssessment)
        .where(DiagnosticAssessment.organization_id == organization_id)
        .order_by(DiagnosticAssessment.assessed_at.desc(), DiagnosticAssessment.id.desc())
        .limit(1)
    )


def get_assessment(session: Session, organization_id: int, assessment_id: int) -> DiagnosticAssessment | None:
    return session.scalar(
        select(DiagnosticAssessment).where(
            DiagnosticAssessment.id == assessment_id,
            DiagnosticAssessment.organization_id == organization_id,
        )
    )


def list_implementation_plans(session: Session, organization_id: int) -> list[ImplementationPlan]:
    return list(
        session.scalars(
            select(ImplementationPlan)
            .options(selectinload(ImplementationPlan.items), selectinload(ImplementationPlan.assessment))
            .where(ImplementationPlan.organization_id == organization_id)
            .order_by(ImplementationPlan.created_at.desc(), ImplementationPlan.id.desc())
        )
    )


def get_implementation_plan(session: Session, organization_id: int, plan_id: int) -> ImplementationPlan | None:
    return session.scalar(
        select(ImplementationPlan)
        .options(selectinload(ImplementationPlan.items), selectinload(ImplementationPlan.assessment))
        .where(
            ImplementationPlan.id == plan_id,
            ImplementationPlan.organization_id == organization_id,
        )
    )
