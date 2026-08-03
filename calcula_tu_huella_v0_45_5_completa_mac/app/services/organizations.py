from __future__ import annotations

from sqlalchemy.orm import Session

from ..database import Facility, Organization, add_audit
from ..repositories.organizations import get_facility


def update_organization(
    session: Session,
    organization: Organization,
    *,
    actor_email: str,
    name: str,
    trade_name: str,
    tax_id: str,
    sector: str,
    ciiu_code: str,
    country: str,
    department: str,
    city: str,
    employees: int,
    contact_name: str,
    contact_email: str,
) -> Organization:
    organization.name = name.strip()
    organization.trade_name = trade_name.strip()
    organization.tax_id = tax_id.strip()
    organization.sector = sector.strip()
    organization.ciiu_code = ciiu_code.strip()
    organization.country = country.strip()
    organization.department = department.strip()
    organization.city = city.strip()
    organization.employees = max(employees, 0)
    organization.contact_name = contact_name.strip()
    organization.contact_email = contact_email.strip()
    add_audit(
        session,
        organization.id,
        actor_email,
        "EDITAR",
        "Organización",
        organization.name,
        "Actualización de la ficha maestra",
    )
    return organization


def create_facility(
    session: Session,
    organization_id: int,
    *,
    actor_email: str,
    name: str,
    facility_type: str,
    city: str,
    address: str,
    employees: int,
    ownership_percentage: float,
    operational_control: bool,
    financial_control: bool,
) -> Facility:
    facility = Facility(
        organization_id=organization_id,
        name=name.strip(),
        facility_type=facility_type.strip(),
        city=city.strip(),
        address=address.strip(),
        employees=max(employees, 0),
        ownership_percentage=max(0, min(ownership_percentage, 100)),
        operational_control=operational_control,
        financial_control=financial_control,
    )
    session.add(facility)
    session.flush()
    add_audit(
        session,
        organization_id,
        actor_email,
        "CREAR",
        "Sede",
        facility.name,
        f"{facility.facility_type} · {facility.city}",
    )
    return facility


def update_facility(
    session: Session,
    organization_id: int,
    facility_id: int,
    *,
    actor_email: str,
    name: str,
    facility_type: str,
    city: str,
    address: str,
    employees: int,
    ownership_percentage: float,
    operational_control: bool,
    financial_control: bool,
    active: bool,
) -> Facility | None:
    facility = get_facility(session, organization_id, facility_id)
    if not facility:
        return None
    facility.name = name.strip()
    facility.facility_type = facility_type.strip()
    facility.city = city.strip()
    facility.address = address.strip()
    facility.employees = max(employees, 0)
    facility.ownership_percentage = max(0, min(ownership_percentage, 100))
    facility.operational_control = operational_control
    facility.financial_control = financial_control
    facility.active = active
    add_audit(
        session,
        organization_id,
        actor_email,
        "EDITAR",
        "Sede",
        facility.name,
        "Actualización de controles y ubicación",
    )
    return facility
