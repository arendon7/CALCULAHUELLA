from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import (
    DataImportBatch,
    DataQualityFinding,
    Inventory,
    PeriodClose,
    ReductionAction,
    ReportArtifact,
    ReviewObservation,
    SupportMessage,
    SupportTicket,
    WorkItem,
    WorkItemEvent,
    WorkItemLink,
    add_audit,
)
from .workflow_domain import DEFAULT_STAGE_BY_WORK_TYPE


ROLE_NAMES = {"Administrador", "Consultor", "Cliente", "Revisor", "Verificador"}


@dataclass(frozen=True, slots=True)
class WorkSourceSpec:
    entity_type: str
    entity_id: int
    organization_id: int
    inventory_id: int | None
    work_type: str
    title: str
    description: str
    status_code: str
    priority: str
    assignee_email: str
    assignee_role: str
    assignee_area: str
    due_date: date | None
    acceptance_criteria: str
    next_action: str
    source_route: str
    closed_at: datetime | None = None


def _normalized(value: str | None) -> str:
    return (value or "").strip()


def _key(value: str | None) -> str:
    return _normalized(value).casefold()


def _inventory_route(inventory_id: int | None) -> str:
    return f"/inventarios/{inventory_id}" if inventory_id is not None else "/inventario"


def _assignment(value: str | None, default_role: str) -> tuple[str, str, str]:
    target = _normalized(value)
    if "@" in target:
        return target.casefold(), "", ""
    if target in ROLE_NAMES:
        return "", target, ""
    return "", default_role, target


def _priority(value: str | None) -> str:
    key = _key(value)
    if key in {"critica", "crítica", "critical", "error crítico", "error critico"}:
        return "critical"
    if key in {"alta", "high", "mayor", "error", "bloqueante"}:
        return "high"
    if key in {"baja", "low", "menor", "informativa"}:
        return "low"
    return "normal"


def _next_action(status_code: str) -> str:
    return {
        "assigned": "Aceptar la asignación y comenzar la preparación.",
        "accepted_by_assignee": "Iniciar la preparación de la entrega.",
        "in_progress": "Completar la preparación y entregar para validación.",
        "blocked": "Resolver el bloqueo documentado antes de reanudar.",
        "submitted": "La entrega espera validación.",
        "validating": "Validar integridad, formato y criterio de aceptación.",
        "under_review": "La entrega espera revisión técnica.",
        "accepted_by_reviewer": "Cerrar la tarea y actualizar el registro relacionado.",
        "returned": "Corregir los puntos indicados y entregar nuevamente.",
        "closed": "Tarea cerrada.",
        "cancelled": "Tarea cancelada con motivo documentado.",
    }.get(status_code, "Revisar el registro y definir la acción siguiente.")


def _snapshot(item: WorkItem | None) -> tuple[Any, ...] | None:
    if item is None:
        return None
    return (
        item.inventory_id,
        item.stage_code,
        item.work_type,
        item.title,
        item.description,
        item.status_code,
        item.priority,
        item.assignee_email,
        item.assignee_role,
        item.assignee_area,
        item.due_date,
        item.acceptance_criteria,
        item.next_action,
        item.source_route,
        item.closed_at,
    )


def _upsert(session: Session, spec: WorkSourceSpec, actor_email: str) -> tuple[WorkItem, bool]:
    item = session.scalar(
        select(WorkItem).where(
            WorkItem.organization_id == spec.organization_id,
            WorkItem.source_entity_type == spec.entity_type,
            WorkItem.source_entity_id == spec.entity_id,
        )
    )
    before = _snapshot(item)
    if item is None:
        item = WorkItem(
            organization_id=spec.organization_id,
            inventory_id=spec.inventory_id,
            stage_code=DEFAULT_STAGE_BY_WORK_TYPE[spec.work_type],
            work_type=spec.work_type,
            title=spec.title,
            description=spec.description,
            status_code=spec.status_code,
            priority=spec.priority,
            requester_email=actor_email,
            assignee_email=spec.assignee_email,
            assignee_role=spec.assignee_role,
            assignee_area=spec.assignee_area,
            due_date=spec.due_date,
            acceptance_criteria=spec.acceptance_criteria,
            next_action=spec.next_action,
            source_entity_type=spec.entity_type,
            source_entity_id=spec.entity_id,
            source_route=spec.source_route,
            created_by=actor_email,
            closed_at=spec.closed_at,
        )
        session.add(item)
        session.flush()
        session.add(
            WorkItemLink(
                work_item_id=item.id,
                entity_type=spec.entity_type,
                entity_id=spec.entity_id,
                relationship_type="origin",
                label=spec.title,
                route=spec.source_route,
            )
        )
        session.add(
            WorkItemEvent(
                work_item_id=item.id,
                event_code="synced_from_source",
                from_status_code="",
                to_status_code=spec.status_code,
                actor_email=actor_email,
                actor_role="Sistema",
                comment=f"{spec.entity_type} #{spec.entity_id} incorporado a Mi trabajo.",
            )
        )
        add_audit(
            session,
            spec.organization_id,
            actor_email,
            "SINCRONIZAR",
            "Trabajo",
            spec.title,
            detail=f"{spec.entity_type} #{spec.entity_id}",
        )
        return item, True

    values = {
        "inventory_id": spec.inventory_id,
        "stage_code": DEFAULT_STAGE_BY_WORK_TYPE[spec.work_type],
        "work_type": spec.work_type,
        "title": spec.title,
        "description": spec.description,
        "priority": spec.priority,
        "assignee_email": spec.assignee_email,
        "assignee_role": spec.assignee_role,
        "assignee_area": spec.assignee_area,
        "due_date": spec.due_date,
        "acceptance_criteria": spec.acceptance_criteria,
        "source_route": spec.source_route,
    }
    for field, value in values.items():
        if getattr(item, field) != value:
            setattr(item, field, value)

    link_changed = False
    origin_link = session.scalar(
        select(WorkItemLink).where(
            WorkItemLink.work_item_id == item.id,
            WorkItemLink.entity_type == spec.entity_type,
            WorkItemLink.entity_id == spec.entity_id,
            WorkItemLink.relationship_type == "origin",
        )
    )
    if origin_link is None:
        session.add(
            WorkItemLink(
                work_item_id=item.id,
                entity_type=spec.entity_type,
                entity_id=spec.entity_id,
                relationship_type="origin",
                label=spec.title,
                route=spec.source_route,
            )
        )
        link_changed = True
    else:
        if origin_link.route != spec.source_route:
            origin_link.route = spec.source_route
            link_changed = True
        if origin_link.label != spec.title:
            origin_link.label = spec.title
            link_changed = True

    if item.status_code != spec.status_code:
        previous = item.status_code
        item.status_code = spec.status_code
        item.next_action = spec.next_action
        item.closed_at = spec.closed_at
        item.version += 1
        item.updated_at = datetime.now(UTC)
        session.add(
            WorkItemEvent(
                work_item_id=item.id,
                event_code="synced_from_source",
                from_status_code=previous,
                to_status_code=spec.status_code,
                actor_email=actor_email,
                actor_role="Sistema",
                comment=f"Estado actualizado desde {spec.entity_type} #{spec.entity_id}.",
            )
        )
    elif item.next_action != spec.next_action:
        item.next_action = spec.next_action
    if spec.status_code != "closed" and item.closed_at is not None:
        item.closed_at = None
    return item, link_changed or before != _snapshot(item)


def _observation_status(value: str) -> str:
    key = _key(value)
    if key in {"cerrada", "cerrado"}:
        return "closed"
    if key in {"resuelta", "resuelto", "aceptada", "aceptado"}:
        return "accepted_by_reviewer"
    if key in {"respondida", "respondido"}:
        return "submitted"
    if key in {"en revisión", "en revision"}:
        return "under_review"
    if key in {"devuelta", "devuelto"}:
        return "returned"
    return "assigned"


def _quality_status(value: str) -> str:
    key = _key(value)
    if key in {"resuelto", "resuelta", "cerrado", "cerrada"}:
        return "closed"
    if key in {"ignorado", "ignorada", "no aplica"}:
        return "cancelled"
    if key in {"en revisión", "en revision"}:
        return "under_review"
    return "assigned"


def _period_status(value: str) -> str:
    key = _key(value)
    if key in {"cerrado", "cerrada"}:
        return "closed"
    if key in {"reabierto", "reabierta", "devuelto", "devuelta"}:
        return "returned"
    if key in {"enviado", "enviada", "en revisión", "en revision"}:
        return "under_review"
    if key in {"en preparación", "en preparacion"}:
        return "in_progress"
    return "assigned"


def _report_status(value: str) -> str:
    key = _key(value)
    if key in {"aprobado", "aprobada", "publicado", "publicada"}:
        return "closed"
    if key in {"devuelto", "devuelta"}:
        return "returned"
    if key in {"en revisión", "en revision"}:
        return "under_review"
    if key in {"generado", "generada"}:
        return "submitted"
    return "in_progress"


def _reduction_status(value: str) -> str:
    key = _key(value)
    if key in {"implementada", "implementado", "completada", "completado"}:
        return "closed"
    if key in {"descartada", "descartado", "cancelada", "cancelado"}:
        return "cancelled"
    if key in {"pausada", "pausado", "bloqueada", "bloqueado"}:
        return "blocked"
    if key in {"en implementación", "en implementacion", "en seguimiento", "en evaluación", "en evaluacion"}:
        return "in_progress"
    return "assigned"


def _support_status(value: str) -> str:
    key = _key(value)
    if key in {"cerrado", "cerrada"}:
        return "closed"
    if key in {"resuelto", "resuelta"}:
        return "accepted_by_reviewer"
    if key in {"esperando cliente", "pendiente cliente", "devuelto", "devuelta"}:
        return "returned"
    if key in {"en revisión", "en revision"}:
        return "under_review"
    if key in {"en curso", "en gestión", "en gestion", "asignado", "asignada"}:
        return "in_progress"
    if key in {"bloqueado", "bloqueada"}:
        return "blocked"
    return "assigned"


def _sync_review_observations(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(ReviewObservation)
            .join(Inventory, Inventory.id == ReviewObservation.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(ReviewObservation.id)
        )
    )
    changed = 0
    for record in records:
        status = _observation_status(record.status)
        default_role = "Revisor" if status in {"submitted", "under_review", "accepted_by_reviewer"} else "Cliente"
        email, role, area = _assignment(record.assigned_to, default_role)
        spec = WorkSourceSpec(
            entity_type="ReviewObservation",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.inventory_id,
            work_type="inventory_review",
            title=f"Resolver observación: {record.title}",
            description=record.description,
            status_code=status,
            priority=_priority(record.severity),
            assignee_email=email,
            assignee_role=role,
            assignee_area=area,
            due_date=record.due_date,
            acceptance_criteria="Responder la observación con corrección, evidencia y explicación suficiente para su revisión.",
            next_action=_next_action(status),
            source_route=_inventory_route(record.inventory_id),
            closed_at=record.closed_at,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def _sync_quality_findings(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(DataQualityFinding)
            .join(DataImportBatch, DataImportBatch.id == DataQualityFinding.batch_id)
            .where(DataImportBatch.organization_id == organization_id)
            .order_by(DataQualityFinding.id)
        )
    )
    changed = 0
    for record in records:
        status = _quality_status(record.status)
        spec = WorkSourceSpec(
            entity_type="DataQualityFinding",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.batch.inventory_id,
            work_type="quality_finding",
            title=f"Corregir hallazgo de calidad {record.rule_code}",
            description=record.message,
            status_code=status,
            priority=_priority(record.severity),
            assignee_email="",
            assignee_role="Revisor" if status == "under_review" else "Cliente",
            assignee_area="",
            due_date=None,
            acceptance_criteria="Corregir el registro afectado o documentar una resolución técnicamente suficiente.",
            next_action=_next_action(status),
            source_route=f"/calidad-datos?batch_id={record.batch_id}",
            closed_at=record.resolved_at if status == "closed" else None,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def _sync_period_closes(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(PeriodClose)
            .where(PeriodClose.organization_id == organization_id)
            .order_by(PeriodClose.period_start, PeriodClose.id)
        )
    )
    changed = 0
    for record in records:
        status = _period_status(record.status)
        period_label = record.period_start.strftime("%m/%Y")
        spec = WorkSourceSpec(
            entity_type="PeriodClose",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.inventory_id,
            work_type="monthly_close",
            title=f"Validar y cerrar el periodo {period_label}",
            description=(
                f"Cobertura de datos {record.data_coverage_percent}% · "
                f"evidencias {record.evidence_coverage_percent}% · "
                f"calidad {record.quality_score}%."
            ),
            status_code=status,
            priority="high" if record.blocked_sources else "normal",
            assignee_email="",
            assignee_role="Revisor" if status in {"under_review", "accepted_by_reviewer"} else "Cliente",
            assignee_area="",
            due_date=record.period_end,
            acceptance_criteria="Resolver bloqueadores, confirmar cobertura y registrar el cierre o devolución del periodo.",
            next_action=_next_action(status),
            source_route=_inventory_route(record.inventory_id),
            closed_at=record.closed_at,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def _sync_reports(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(ReportArtifact)
            .join(Inventory, Inventory.id == ReportArtifact.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(ReportArtifact.generated_at, ReportArtifact.id)
        )
    )
    changed = 0
    for record in records:
        status = _report_status(record.status)
        spec = WorkSourceSpec(
            entity_type="ReportArtifact",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.inventory_id,
            work_type="report_approval",
            title=f"Aprobar {record.report_type} · versión {record.version}",
            description=f"Artefacto {record.file_name} generado por {record.generated_by}.",
            status_code=status,
            priority="normal",
            assignee_email="",
            assignee_role="Consultor" if status == "returned" else "Revisor",
            assignee_area="",
            due_date=None,
            acceptance_criteria="Confirmar integridad, versión, nivel de uso y autorización antes de publicar o entregar.",
            next_action=_next_action(status),
            source_route=_inventory_route(record.inventory_id),
            closed_at=record.approved_at if status == "closed" else None,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def _sync_reduction_actions(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(ReductionAction)
            .join(Inventory, Inventory.id == ReductionAction.inventory_id)
            .where(Inventory.organization_id == organization_id)
            .order_by(ReductionAction.id)
        )
    )
    changed = 0
    for record in records:
        status = _reduction_status(record.status)
        email, role, area = _assignment(record.responsible, "Cliente")
        spec = WorkSourceSpec(
            entity_type="ReductionAction",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.inventory_id,
            work_type="reduction_action",
            title=f"Gestionar reducción: {record.title}",
            description=record.description,
            status_code=status,
            priority=_priority(record.priority),
            assignee_email=email,
            assignee_role=role,
            assignee_area=area,
            due_date=record.target_date,
            acceptance_criteria="Registrar avance, evidencia de implementación, resultados observados y decisión de continuidad.",
            next_action=_next_action(status),
            source_route=_inventory_route(record.inventory_id),
            closed_at=record.updated_at if status == "closed" else None,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def _sync_support_tickets(session: Session, organization_id: int, actor_email: str) -> dict[str, int]:
    records = list(
        session.scalars(
            select(SupportTicket)
            .where(SupportTicket.organization_id == organization_id)
            .order_by(SupportTicket.created_at, SupportTicket.id)
        )
    )
    changed = 0
    for record in records:
        status = _support_status(record.status)
        waiting_client = status == "returned"
        email, role, area = _assignment(
            record.created_by if waiting_client else record.assigned_to,
            "Cliente" if waiting_client else "Consultor",
        )
        spec = WorkSourceSpec(
            entity_type="SupportTicket",
            entity_id=record.id,
            organization_id=organization_id,
            inventory_id=record.inventory_id,
            work_type="support_follow_up",
            title=f"Atender conversación: {record.subject}",
            description=record.description,
            status_code=status,
            priority=_priority(record.priority),
            assignee_email=email,
            assignee_role=role,
            assignee_area=area,
            due_date=record.due_date,
            acceptance_criteria=record.desired_outcome.strip() or "Registrar respuesta, decisión y resolución verificable de la conversación.",
            next_action=_next_action(status),
            source_route=f"/soporte?ticket_id={record.id}",
            closed_at=record.closed_at,
        )
        _, item_changed = _upsert(session, spec, actor_email)
        changed += int(item_changed)
    return {"total": len(records), "changed": changed}


def sync_specialized_work_items(session: Session, organization_id: int, actor_email: str) -> dict[str, Any]:
    sources = {
        "review_observations": _sync_review_observations(session, organization_id, actor_email),
        "quality_findings": _sync_quality_findings(session, organization_id, actor_email),
        "period_closes": _sync_period_closes(session, organization_id, actor_email),
        "reports": _sync_reports(session, organization_id, actor_email),
        "reduction_actions": _sync_reduction_actions(session, organization_id, actor_email),
        "support_tickets": _sync_support_tickets(session, organization_id, actor_email),
    }
    return {
        "total": sum(result["total"] for result in sources.values()),
        "changed": sum(result["changed"] for result in sources.values()),
        "sources": sources,
    }


def mirror_source_from_work_item(
    session: Session,
    item: WorkItem,
    *,
    actor_email: str,
    actor_role: str,
    comment: str = "",
) -> bool:
    now = datetime.now(UTC)
    source_type = item.source_entity_type
    source_id = item.source_entity_id
    if not source_type or not source_id:
        return False

    if source_type == "ReviewObservation":
        record = session.get(ReviewObservation, source_id)
        if not record:
            return False
        record.status = {
            "submitted": "Respondida",
            "validating": "En revisión",
            "under_review": "En revisión",
            "accepted_by_reviewer": "Resuelta",
            "returned": "Devuelta",
            "closed": "Cerrada",
            "cancelled": "Cerrada",
        }.get(item.status_code, "Abierta")
        if item.status_code == "submitted":
            record.response = comment.strip() or record.response
            record.responded_by = actor_email
            record.responded_at = now
        if item.status_code in {"accepted_by_reviewer", "closed"}:
            record.resolution = comment.strip() or record.resolution
            record.resolved_by = actor_email
            record.resolved_at = now
        if item.status_code in {"closed", "cancelled"}:
            record.closed_by = actor_email
            record.closed_at = now
        elif record.closed_at is not None:
            record.closed_at = None
            record.closed_by = ""
        return True

    if source_type == "DataQualityFinding":
        record = session.get(DataQualityFinding, source_id)
        if not record:
            return False
        record.status = {
            "validating": "En revisión",
            "under_review": "En revisión",
            "accepted_by_reviewer": "En revisión",
            "closed": "Resuelto",
            "cancelled": "Ignorado",
        }.get(item.status_code, "Abierto")
        if item.status_code in {"closed", "cancelled"}:
            record.resolution = comment.strip() or record.resolution
            record.resolved_at = now
        elif record.resolved_at is not None:
            record.resolved_at = None
        return True

    if source_type == "PeriodClose":
        record = session.get(PeriodClose, source_id)
        if not record:
            return False
        record.status = {
            "submitted": "En revisión",
            "validating": "En revisión",
            "under_review": "En revisión",
            "accepted_by_reviewer": "En revisión",
            "returned": "Reabierto",
            "closed": "Cerrado",
        }.get(item.status_code, "Abierto")
        if item.status_code == "closed":
            record.closed_by = actor_email
            record.closed_at = now
        elif item.status_code == "returned":
            record.reopened_by = actor_email
            record.reopened_at = now
            record.reopen_reason = comment.strip() or record.reopen_reason
            record.closed_by = ""
            record.closed_at = None
        elif record.closed_at is not None:
            record.closed_by = ""
            record.closed_at = None
        return True

    if source_type == "ReportArtifact":
        record = session.get(ReportArtifact, source_id)
        if not record:
            return False
        record.status = {
            "in_progress": "Borrador",
            "submitted": "Generado",
            "validating": "En revisión",
            "under_review": "En revisión",
            "returned": "Devuelto",
            "accepted_by_reviewer": "Aprobado",
            "closed": "Aprobado",
        }.get(item.status_code, record.status)
        if item.status_code in {"accepted_by_reviewer", "closed"}:
            record.approved_by = actor_email
            record.approved_at = now
        elif item.status_code == "returned":
            record.approved_by = ""
            record.approved_at = None
        return True

    if source_type == "ReductionAction":
        record = session.get(ReductionAction, source_id)
        if not record:
            return False
        record.status = {
            "assigned": "Identificada",
            "accepted_by_assignee": "En implementación",
            "in_progress": "En implementación",
            "blocked": "Pausada",
            "submitted": "En seguimiento",
            "validating": "En seguimiento",
            "under_review": "En seguimiento",
            "accepted_by_reviewer": "En seguimiento",
            "returned": "En evaluación",
            "closed": "Implementada",
            "cancelled": "Descartada",
        }.get(item.status_code, record.status)
        if item.status_code == "closed":
            record.progress_percent = 100
        return True

    if source_type == "SupportTicket":
        record = session.get(SupportTicket, source_id)
        if not record:
            return False
        record.status = {
            "assigned": "Abierto",
            "accepted_by_assignee": "En gestión",
            "in_progress": "En gestión",
            "blocked": "Bloqueado",
            "submitted": "En revisión",
            "validating": "En revisión",
            "under_review": "En revisión",
            "accepted_by_reviewer": "Resuelto",
            "returned": "Esperando cliente",
            "closed": "Cerrado",
            "cancelled": "Cerrado",
        }.get(item.status_code, record.status)
        record.updated_at = now
        if comment.strip():
            session.add(
                SupportMessage(
                    ticket_id=record.id,
                    author_email=actor_email,
                    author_role=actor_role,
                    message_type="Seguimiento de tarea",
                    body=comment.strip(),
                    visible_to_client=True,
                )
            )
            record.last_message_at = now
        if item.status_code in {"accepted_by_reviewer", "closed"}:
            record.resolution = comment.strip() or record.resolution
        if item.status_code in {"closed", "cancelled"}:
            record.closed_at = now
        elif record.closed_at is not None:
            record.closed_at = None
        return True

    return False
