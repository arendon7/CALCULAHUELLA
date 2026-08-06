from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .database import AuditEvent, Base, Organization, audit_event_digest


@dataclass(frozen=True)
class IntegrityIssue:
    code: str
    table: str
    count: int
    detail: str
    critical: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# These cross-organization relations are intentional: a user can belong to more
# than one company and notifications may target that shared user in the active
# company. They are checked with membership-aware rules below.
_ALLOWED_CROSS_ORG_FOREIGN_KEYS = {
    ("organization_memberships", "user_id"),
    ("notifications", "user_id"),
}


def _count(session: Session, statement) -> int:
    return int(session.scalar(statement) or 0)


def audit_tenant_integrity(session: Session) -> dict[str, Any]:
    """Audit cross-company consistency without changing data.

    The audit combines generic checks for every table carrying organization_id
    with explicit checks for the inventory graph. It is designed for release
    certification, backup drills and diagnostics, not as a replacement for
    request-time authorization.
    """
    issues: list[IntegrityIssue] = []
    checks: list[dict[str, Any]] = []
    organizations = Base.metadata.tables["organizations"]

    for table_name in sorted(Base.metadata.tables):
        table = Base.metadata.tables[table_name]
        if "organization_id" not in table.c:
            continue

        orphan_count = _count(
            session,
            select(func.count())
            .select_from(table.outerjoin(organizations, table.c.organization_id == organizations.c.id))
            .where(table.c.organization_id.is_not(None), organizations.c.id.is_(None)),
        )
        checks.append({
            "code": f"{table_name}.organization_exists",
            "ok": orphan_count == 0,
            "count": orphan_count,
        })
        if orphan_count:
            issues.append(IntegrityIssue(
                code="ORPHAN_ORGANIZATION",
                table=table_name,
                count=orphan_count,
                detail="Filas con organization_id inexistente.",
            ))

        for foreign_key in sorted(table.foreign_keys, key=lambda item: item.parent.name):
            local_column = foreign_key.parent
            target_column = foreign_key.column
            target_table = target_column.table
            if (table_name, local_column.name) in _ALLOWED_CROSS_ORG_FOREIGN_KEYS:
                continue
            if "organization_id" not in target_table.c:
                continue
            if target_table is table:
                target_alias = target_table.alias(f"{target_table.name}_parent")
                join_target = target_alias
                join_condition = local_column == target_alias.c[target_column.name]
                target_org_column = target_alias.c.organization_id
            else:
                join_target = target_table
                join_condition = local_column == target_column
                target_org_column = target_table.c.organization_id
            mismatch_count = _count(
                session,
                select(func.count())
                .select_from(table.join(join_target, join_condition))
                .where(table.c.organization_id != target_org_column),
            )
            check_code = f"{table_name}.{local_column.name}.same_organization"
            checks.append({"code": check_code, "ok": mismatch_count == 0, "count": mismatch_count})
            if mismatch_count:
                issues.append(IntegrityIssue(
                    code="CROSS_TENANT_FOREIGN_KEY",
                    table=table_name,
                    count=mismatch_count,
                    detail=(
                        f"{local_column.name} apunta a {target_table.name} de otra organización."
                    ),
                ))

    inventories = Base.metadata.tables["inventories"]
    facilities = Base.metadata.tables["facilities"]
    inventory_facilities = Base.metadata.tables["inventory_facilities"]
    emission_sources = Base.metadata.tables["emission_sources"]
    evidence_documents = Base.metadata.tables["evidence_documents"]
    data_requests = Base.metadata.tables["data_requests"]
    activity_data = Base.metadata.tables["activity_data"]
    notifications = Base.metadata.tables["notifications"]
    app_users = Base.metadata.tables["app_users"]
    memberships = Base.metadata.tables["organization_memberships"]

    special_queries = [
        (
            "inventory_facilities.same_organization",
            inventory_facilities
            .join(inventories, inventory_facilities.c.inventory_id == inventories.c.id)
            .join(facilities, inventory_facilities.c.facility_id == facilities.c.id),
            inventories.c.organization_id != facilities.c.organization_id,
            "INVENTORY_FACILITY_CROSS_TENANT",
            "Una sede asociada al inventario pertenece a otra organización.",
        ),
        (
            "emission_sources.facility_same_organization",
            emission_sources
            .join(inventories, emission_sources.c.inventory_id == inventories.c.id)
            .join(facilities, emission_sources.c.facility_id == facilities.c.id),
            and_(emission_sources.c.facility_id.is_not(None), inventories.c.organization_id != facilities.c.organization_id),
            "SOURCE_FACILITY_CROSS_TENANT",
            "Una fuente usa una sede de otra organización.",
        ),
        (
            "evidence_documents.source_same_inventory",
            evidence_documents.join(emission_sources, evidence_documents.c.source_id == emission_sources.c.id),
            and_(evidence_documents.c.source_id.is_not(None), evidence_documents.c.inventory_id != emission_sources.c.inventory_id),
            "EVIDENCE_SOURCE_CROSS_INVENTORY",
            "Una evidencia referencia una fuente de otro inventario.",
        ),
        (
            "data_requests.source_same_inventory",
            data_requests.join(emission_sources, data_requests.c.source_id == emission_sources.c.id),
            and_(data_requests.c.source_id.is_not(None), data_requests.c.inventory_id != emission_sources.c.inventory_id),
            "REQUEST_SOURCE_CROSS_INVENTORY",
            "Una solicitud referencia una fuente de otro inventario.",
        ),
        (
            "activity_data.evidence_same_inventory",
            activity_data
            .join(emission_sources, activity_data.c.source_id == emission_sources.c.id)
            .join(evidence_documents, activity_data.c.evidence_id == evidence_documents.c.id),
            and_(activity_data.c.evidence_id.is_not(None), emission_sources.c.inventory_id != evidence_documents.c.inventory_id),
            "ACTIVITY_EVIDENCE_CROSS_INVENTORY",
            "Un dato de actividad usa evidencia perteneciente a otro inventario.",
        ),
    ]
    for check_code, join_clause, condition, issue_code, detail in special_queries:
        mismatch_count = _count(session, select(func.count()).select_from(join_clause).where(condition))
        checks.append({"code": check_code, "ok": mismatch_count == 0, "count": mismatch_count})
        if mismatch_count:
            issues.append(IntegrityIssue(issue_code, check_code.split(".", 1)[0], mismatch_count, detail))

    notification_without_access = _count(
        session,
        select(func.count())
        .select_from(notifications.join(app_users, notifications.c.user_id == app_users.c.id))
        .where(
            and_(
                notifications.c.user_id.is_not(None),
                app_users.c.organization_id != notifications.c.organization_id,
                ~select(memberships.c.id)
                .where(
                    memberships.c.user_id == notifications.c.user_id,
                    memberships.c.organization_id == notifications.c.organization_id,
                    memberships.c.active.is_(True),
                )
                .exists(),
            )
        ),
    )
    checks.append({
        "code": "notifications.user_has_organization_access",
        "ok": notification_without_access == 0,
        "count": notification_without_access,
    })
    if notification_without_access:
        issues.append(IntegrityIssue(
            "NOTIFICATION_USER_WITHOUT_ACCESS",
            "notifications",
            notification_without_access,
            "Una notificación está asignada a un usuario sin acceso activo a la organización.",
        ))

    organization_count = _count(session, select(func.count(Organization.id)))
    critical_count = sum(item.count for item in issues if item.critical)
    return {
        "ok": critical_count == 0,
        "organization_count": organization_count,
        "checks_run": len(checks),
        "critical_issue_count": critical_count,
        "issues": [item.as_dict() for item in issues],
        "checks": checks,
    }


def audit_chain_integrity(session: Session) -> dict[str, Any]:
    """Validate the immutable audit chain independently for each company."""
    failures: list[dict[str, Any]] = []
    checked = 0
    organization_ids = list(session.scalars(select(AuditEvent.organization_id).distinct()))
    for organization_id in organization_ids:
        previous_hash = ""
        events = list(session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id)
        ))
        for event in events:
            checked += 1
            expected = audit_event_digest(event, previous_hash)
            if event.previous_hash != previous_hash or event.event_hash != expected:
                failures.append({
                    "organization_id": organization_id,
                    "event_id": event.id,
                    "expected": expected,
                    "stored": event.event_hash,
                })
            previous_hash = event.event_hash or expected
    return {
        "ok": not failures,
        "checked": checked,
        "failure_count": len(failures),
        "failures": failures[:20],
    }
