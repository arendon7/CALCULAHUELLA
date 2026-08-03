from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from .database import (
    ActivityData,
    DataImportBatch,
    DataImportRow,
    DataQualityFinding,
    EmissionCalculation,
    EmissionFactorVersion,
    EmissionSource,
    PeriodClose,
    PeriodCloseItem,
    PilotExecution,
    PilotExecutionSourceLink,
    PilotProject,
    SourceFactorAssignment,
    add_audit,
)

PERIOD_CLOSE_VERSION = "0.27.0"
MONTH_NAMES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
FACTOR_READY_PREFIXES = ("Formal", "Piloto")
FACTOR_READY_VALUES = {"Aprobado", "Indicador", "Dato de actividad", "No aplica"}


def month_bounds(year: int, month: int) -> tuple[date, date]:
    if month < 1 or month > 12:
        raise ValueError("Mes inválido")
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def parse_period_key(value: str | None, fallback_year: int) -> tuple[date, date]:
    if value:
        try:
            year, month = (int(part) for part in value.split("-", 1))
            return month_bounds(year, month)
        except (TypeError, ValueError):
            pass
    return month_bounds(fallback_year, 1)


def _execution(session: Session, organization_id: int) -> PilotExecution | None:
    return session.scalar(
        select(PilotExecution)
        .join(PilotProject)
        .where(PilotProject.organization_id == organization_id, PilotProject.code == "GREENATICS-2026")
        .options(
            selectinload(PilotExecution.inventory),
            selectinload(PilotExecution.source_links).selectinload(PilotExecutionSourceLink.requirement),
            selectinload(PilotExecution.source_links).selectinload(PilotExecutionSourceLink.source),
        )
    )


def _is_expected(frequency: str, period_start: date) -> bool:
    normalized = (frequency or "Mensual").strip().lower()
    if normalized == "anual":
        return period_start.month == 12
    if normalized == "trimestral":
        return period_start.month in {3, 6, 9, 12}
    return True


def _factor_ready(requirement_status: str, scope: int) -> bool:
    status = (requirement_status or "").strip()
    if scope == 0:
        return True
    return status in FACTOR_READY_VALUES or status.startswith(FACTOR_READY_PREFIXES)


def _source_rows(
    session: Session,
    execution: PilotExecution,
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in sorted(execution.source_links, key=lambda item: (item.requirement.site, item.requirement.code)):
        source = link.source
        requirement = link.requirement
        if not source or not source.included or not _is_expected(requirement.frequency, period_start):
            continue
        records = list(
            session.scalars(
                select(ActivityData)
                .where(
                    ActivityData.source_id == source.id,
                    ActivityData.period_start <= period_end,
                    ActivityData.period_end >= period_start,
                )
                .options(selectinload(ActivityData.calculations))
                .order_by(ActivityData.period_start)
            )
        )
        record_ids = [record.id for record in records]
        import_rows: list[DataImportRow] = []
        if record_ids:
            import_rows = list(
                session.scalars(
                    select(DataImportRow).where(DataImportRow.activity_data_id.in_(record_ids))
                )
            )
        evidence_count = sum(bool(record.evidence_id or "Evidencia:" in (record.notes or "")) for record in records)
        evidence_count += sum(bool(row.evidence_reference.strip()) for row in import_rows)
        estimated_count = sum(bool(record.is_estimated) for record in records)
        calculation_count = sum(len(record.calculations) for record in records)
        emissions_kg = sum(calc.co2e_kg for record in records for calc in record.calculations)
        open_findings = 0
        blocking_findings = 0
        if record_ids:
            findings = list(
                session.scalars(
                    select(DataQualityFinding)
                    .join(DataImportRow)
                    .join(DataImportBatch)
                    .where(
                        DataImportBatch.organization_id == execution.pilot.organization_id,
                        DataImportRow.activity_data_id.in_(record_ids),
                        DataQualityFinding.status == "Abierto",
                    )
                )
            )
            open_findings = len(findings)
            blocking_findings = sum(item.severity == "Error" for item in findings)
        factor_ready = _factor_ready(requirement.factor_status, requirement.scope)
        blockers: list[str] = []
        warnings: list[str] = []
        if not records:
            blockers.append("Sin dato para el periodo")
        if records and requirement.materiality == "Alta" and evidence_count == 0:
            blockers.append("Fuente material sin evidencia")
        if blocking_findings:
            blockers.append(f"{blocking_findings} hallazgo(s) bloqueante(s)")
        if requirement.scope != 0 and not factor_ready:
            blockers.append("Factor metodológico no aprobado")
        if records and requirement.scope != 0 and factor_ready and calculation_count == 0:
            blockers.append("Dato sin cálculo de emisiones")
        if estimated_count:
            warnings.append(f"{estimated_count} dato(s) estimado(s)")
        if open_findings and not blocking_findings:
            warnings.append(f"{open_findings} advertencia(s) abierta(s)")
        qualities = [record.quality_level or "D" for record in records]
        quality_level = min(qualities, default="D")
        if quality_level in {"C", "D"} and records:
            warnings.append(f"Calidad {quality_level}")
        status = "Bloqueado" if blockers else ("Con advertencias" if warnings else "Listo")
        rows.append(
            {
                "source_id": source.id,
                "code": requirement.code,
                "site": requirement.site,
                "name": requirement.source_name,
                "scope": requirement.scope,
                "materiality": requirement.materiality,
                "frequency": requirement.frequency,
                "factor_status": requirement.factor_status,
                "records": len(records),
                "evidence": evidence_count,
                "estimated": estimated_count,
                "quality": quality_level,
                "calculations": calculation_count,
                "emissions_tco2e": round(emissions_kg / 1000, 6),
                "open_findings": open_findings,
                "blockers": blockers,
                "warnings": warnings,
                "status": status,
            }
        )
    return rows


def _default_period(execution: PilotExecution, session: Session) -> tuple[date, date]:
    year = execution.inventory.start_date.year if execution.inventory else execution.pilot.reporting_year
    latest = session.scalar(
        select(func.max(ActivityData.period_start))
        .join(EmissionSource)
        .where(EmissionSource.inventory_id == execution.inventory_id)
    )
    if latest and latest.year == year:
        return month_bounds(year, latest.month)
    return month_bounds(year, 1)


def period_close_summary(session: Session, organization_id: int, period_key: str | None = None) -> dict[str, Any]:
    execution = _execution(session, organization_id)
    if not execution or not execution.inventory:
        return {"execution": None, "inventory": None, "periods": [], "rows": [], "record": None, "metrics": {}, "blockers": ["Primero inicia el piloto Greenatics."]}
    default_start, default_end = _default_period(execution, session)
    period_start, period_end = parse_period_key(period_key, default_start.year) if period_key else (default_start, default_end)
    if period_start < execution.inventory.start_date or period_end > execution.inventory.end_date:
        raise ValueError("El periodo está fuera del inventario activo")
    rows = _source_rows(session, execution, period_start, period_end)
    blockers = [f"{row['code']}: {message}" for row in rows for message in row["blockers"]]
    warnings = [f"{row['code']}: {message}" for row in rows for message in row["warnings"]]
    ready = sum(row["status"] == "Listo" for row in rows)
    with_warnings = sum(row["status"] == "Con advertencias" for row in rows)
    blocked = sum(row["status"] == "Bloqueado" for row in rows)
    quality_score = max(0, round(100 - (blocked * 8 + len(warnings) * 2))) if rows else 0
    record = session.scalar(
        select(PeriodClose).where(
            PeriodClose.inventory_id == execution.inventory_id,
            PeriodClose.period_start == period_start,
            PeriodClose.period_end == period_end,
        )
    )
    periods = [
        {
            "key": f"{execution.inventory.start_date.year}-{month:02d}",
            "label": f"{MONTH_NAMES[month]} {execution.inventory.start_date.year}",
        }
        for month in range(execution.inventory.start_date.month, execution.inventory.end_date.month + 1)
    ]
    return {
        "execution": execution,
        "inventory": execution.inventory,
        "period_start": period_start,
        "period_end": period_end,
        "period_key": f"{period_start.year}-{period_start.month:02d}",
        "period_label": f"{MONTH_NAMES[period_start.month]} {period_start.year}",
        "periods": periods,
        "rows": rows,
        "record": record,
        "blockers": blockers,
        "warnings": warnings,
        "metrics": {
            "expected": len(rows),
            "ready": ready,
            "warnings": with_warnings,
            "blocked": blocked,
            "data_coverage": round(100 * sum(row["records"] > 0 for row in rows) / max(len(rows), 1)),
            "evidence_coverage": round(100 * sum(row["evidence"] > 0 for row in rows if row["materiality"] == "Alta") / max(sum(row["materiality"] == "Alta" for row in rows), 1)),
            "total_tco2e": round(sum(row["emissions_tco2e"] for row in rows), 6),
            "quality_score": quality_score,
        },
    }


def _get_or_create_close(session: Session, summary: dict[str, Any]) -> PeriodClose:
    record = summary["record"]
    if record:
        return record
    execution = summary["execution"]
    record = PeriodClose(
        organization_id=execution.pilot.organization_id,
        inventory_id=execution.inventory_id,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        status="Abierto",
    )
    session.add(record)
    session.flush()
    summary["record"] = record
    return record


def _sync_metrics(record: PeriodClose, summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    record.expected_sources = metrics["expected"]
    record.ready_sources = metrics["ready"] + metrics["warnings"]
    record.blocked_sources = metrics["blocked"]
    record.data_coverage_percent = metrics["data_coverage"]
    record.evidence_coverage_percent = metrics["evidence_coverage"]
    record.quality_score = metrics["quality_score"]
    record.total_tco2e = metrics["total_tco2e"]
    record.blockers_json = json.dumps(summary["blockers"], ensure_ascii=False)
    record.updated_at = datetime.now(UTC)


def submit_period_close(session: Session, organization_id: int, period_key: str, user_email: str, notes: str = "") -> PeriodClose:
    summary = period_close_summary(session, organization_id, period_key)
    record = _get_or_create_close(session, summary)
    if record.status == "Cerrado":
        raise ValueError("El periodo está cerrado. Debe reabrirse con justificación antes de modificarlo.")
    _sync_metrics(record, summary)
    data_blockers = [item for item in summary["blockers"] if "Sin dato" in item or "evidencia" in item or "hallazgo" in item]
    if data_blockers:
        raise ValueError(f"No puede enviarse a revisión: existen {len(data_blockers)} bloqueo(s) de datos o evidencia.")
    record.status = "En revisión"
    record.notes = notes.strip()
    record.submitted_by = user_email
    record.submitted_at = datetime.now(UTC)
    add_audit(session, organization_id, user_email, "ENVIAR_REVISIÓN", "Cierre mensual", summary["period_label"], detail=f"Cobertura {record.data_coverage_percent}% · {record.blocked_sources} bloqueos metodológicos")
    return record


def _snapshot_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "engine_version": PERIOD_CLOSE_VERSION,
        "inventory_id": summary["inventory"].id,
        "inventory_version": summary["inventory"].version,
        "period_start": summary["period_start"].isoformat(),
        "period_end": summary["period_end"].isoformat(),
        "metrics": summary["metrics"],
        "sources": [
            {
                "source_id": row["source_id"],
                "code": row["code"],
                "site": row["site"],
                "scope": row["scope"],
                "records": row["records"],
                "evidence": row["evidence"],
                "estimated": row["estimated"],
                "quality": row["quality"],
                "calculations": row["calculations"],
                "emissions_tco2e": row["emissions_tco2e"],
                "factor_status": row["factor_status"],
                "status": row["status"],
            }
            for row in summary["rows"]
        ],
    }


def close_period(session: Session, organization_id: int, period_key: str, user_email: str, comments: str = "") -> PeriodClose:
    summary = period_close_summary(session, organization_id, period_key)
    record = _get_or_create_close(session, summary)
    if record.status != "En revisión":
        raise ValueError("El periodo debe estar en revisión antes de cerrarlo.")
    _sync_metrics(record, summary)
    if summary["blockers"]:
        raise ValueError(f"No puede cerrarse: existen {len(summary['blockers'])} bloqueo(s).")
    payload = _snapshot_payload(summary)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    session.execute(delete(PeriodCloseItem).where(PeriodCloseItem.period_close_id == record.id))
    for row in summary["rows"]:
        session.add(
            PeriodCloseItem(
                period_close_id=record.id,
                source_id=row["source_id"],
                source_code=row["code"],
                source_name=row["name"],
                site=row["site"],
                scope=row["scope"],
                activity_records=row["records"],
                evidence_count=row["evidence"],
                estimated_records=row["estimated"],
                quality_level=row["quality"],
                calculation_count=row["calculations"],
                emissions_tco2e=row["emissions_tco2e"],
                status=row["status"],
                snapshot_json=json.dumps(row, ensure_ascii=False, sort_keys=True),
            )
        )
    record.status = "Cerrado"
    record.snapshot_hash = snapshot_hash
    record.snapshot_json = canonical
    record.closed_by = user_email
    record.closed_at = datetime.now(UTC)
    record.reopen_reason = ""
    record.reopened_by = ""
    record.reopened_at = None
    record.notes = " · ".join(filter(None, [record.notes, comments.strip()]))
    add_audit(session, organization_id, user_email, "CERRAR", "Cierre mensual", summary["period_label"], detail=f"Hash {snapshot_hash} · {record.total_tco2e} tCO2e")
    return record


def reopen_period(session: Session, organization_id: int, period_key: str, user_email: str, reason: str) -> PeriodClose:
    if len(reason.strip()) < 10:
        raise ValueError("La justificación de reapertura debe tener al menos 10 caracteres.")
    summary = period_close_summary(session, organization_id, period_key)
    record = summary["record"]
    if not record or record.status != "Cerrado":
        raise ValueError("El periodo no está cerrado.")
    previous_hash = record.snapshot_hash
    record.status = "Reabierto"
    record.reopen_reason = reason.strip()
    record.reopened_by = user_email
    record.reopened_at = datetime.now(UTC)
    add_audit(session, organization_id, user_email, "REABRIR", "Cierre mensual", summary["period_label"], detail=reason.strip(), previous_value=previous_hash, new_value="Periodo reabierto")
    return record


def assert_periods_editable(session: Session, inventory_id: int, periods: list[tuple[date, date]]) -> None:
    for period_start, period_end in periods:
        closed = session.scalar(
            select(PeriodClose.id).where(
                PeriodClose.inventory_id == inventory_id,
                PeriodClose.status == "Cerrado",
                PeriodClose.period_start <= period_end,
                PeriodClose.period_end >= period_start,
            )
        )
        if closed:
            raise ValueError(f"El periodo {period_start:%Y-%m} está cerrado y no admite nuevas cargas. Reábrelo desde Cierre mensual.")
