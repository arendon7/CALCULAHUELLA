from __future__ import annotations

import hashlib
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import DeploymentRehearsal, OperationalIncident
from .observability import metrics
from .operations import diagnostic_snapshot
from .storage import storage


def _check(code: str, label: str, ok: bool, detail: str, critical: bool = True) -> dict[str, object]:
    return {"code": code, "label": label, "ok": bool(ok), "detail": detail, "critical": critical}


def _probe_url(url: str, label: str) -> tuple[bool, str]:
    if not url:
        return False, f"{label} no configurado"
    try:
        request = Request(url, headers={"User-Agent": f"CalculaTuHuella/{settings.version}"})
        with urlopen(request, timeout=max(0.5, settings.external_probe_timeout_seconds)) as response:
            status = int(getattr(response, "status", 200) or 200)
            return 200 <= status < 400, f"HTTP {status} · {url}"
    except HTTPError as exc:
        return False, f"HTTP {exc.code} · {url}"
    except (URLError, OSError, TimeoutError) as exc:
        return False, f"{url} · {exc}"


def production_checks(strict: bool | None = None) -> list[dict[str, object]]:
    strict_mode = settings.deployment_strict if strict is None else strict
    snapshot = diagnostic_snapshot()
    storage_probe = storage.verified_probe()
    metrics_snapshot = metrics.snapshot()
    checks = [
        _check("database", "Conexión a base de datos", bool(snapshot["database_ok"]), str(snapshot["database_detail"])),
        _check(
            "postgresql",
            "PostgreSQL productivo",
            settings.database_backend == "PostgreSQL",
            f"Backend actual: {settings.database_backend}",
            critical=strict_mode,
        ),
        _check("storage", "Almacenamiento lectura/escritura", bool(storage_probe["ok"]), str(storage_probe["detail"])),
        _check(
            "external_storage",
            "Almacenamiento externo",
            settings.storage_backend in {"filesystem", "s3"},
            f"Backend actual: {settings.storage_backend}",
            critical=strict_mode,
        ),
        _check("admin", "Administrador activo", bool(snapshot["admin_ok"]), "Existe al menos un administrador activo." if snapshot["admin_ok"] else "No hay administrador activo."),
        _check("audit", "Cadena de auditoría", bool(snapshot["audit_integrity"]["ok"]), f"{snapshot['audit_integrity']['checked']} eventos revisados"),
        _check("logs", "Registro estructurado", bool(snapshot["structured_log"]["ok"]), f"{snapshot['structured_log']['records']} registros"),
        _check("restore", "Ensayo de restauración vigente", bool(snapshot["restore_drill"]["ok"]), str(snapshot["restore_drill"]["status"]), critical=strict_mode),
        _check("https", "URL HTTPS", str(snapshot["public_base_url"]).startswith("https://"), str(snapshot["public_base_url"]), critical=strict_mode),
        _check("metrics", "Métricas operativas", True, f"{metrics_snapshot['request_count']} solicitudes observadas", critical=False),
        _check("metrics_token", "Protección de métricas", bool(settings.metrics_token), "Token configurado" if settings.metrics_token else "METRICS_TOKEN no configurado", critical=strict_mode),
        _check("alert_secret", "Autenticación de alertas", bool(settings.alert_webhook_secret), "Secreto configurado" if settings.alert_webhook_secret else "ALERT_WEBHOOK_SECRET no configurado", critical=strict_mode),
    ]
    service_specs = (
        ("object_storage_service", "Servicio de almacenamiento", settings.object_storage_health_url),
        ("prometheus_service", "Prometheus", settings.prometheus_health_url),
        ("alertmanager_service", "Alertmanager", settings.alertmanager_health_url),
        ("grafana_service", "Grafana", settings.grafana_health_url),
    )
    for code, label, url in service_specs:
        ok, detail = _probe_url(url, label)
        checks.append(_check(code, label, ok, detail, critical=strict_mode))
    return checks


def _fingerprint(code: str, detail: str) -> str:
    return hashlib.sha256(f"{code}\x1f{detail}".encode("utf-8")).hexdigest()


def sync_incidents(session: Session, organization_id: int, checks: list[dict[str, object]]) -> int:
    now = datetime.now(UTC)
    touched = 0
    active_fingerprints: set[str] = set()
    for item in checks:
        if item["ok"] or not item["critical"]:
            continue
        fingerprint = _fingerprint(str(item["code"]), str(item["detail"]))
        active_fingerprints.add(fingerprint)
        incident = session.scalar(select(OperationalIncident).where(
            OperationalIncident.organization_id == organization_id,
            OperationalIncident.fingerprint == fingerprint,
        ))
        if incident:
            incident.occurrence_count += 1
            incident.last_seen_at = now
            if incident.status == "Resuelto":
                incident.status = "Abierto"
                incident.resolved_at = None
                incident.resolved_by = ""
        else:
            incident = OperationalIncident(
                organization_id=organization_id,
                fingerprint=fingerprint,
                title=str(item["label"]),
                severity="Crítica",
                status="Abierto",
                source="Ensayo de despliegue",
                detail=str(item["detail"]),
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(incident)
        touched += 1
    stale = list(session.scalars(select(OperationalIncident).where(
        OperationalIncident.organization_id == organization_id,
        OperationalIncident.source == "Ensayo de despliegue",
        OperationalIncident.status != "Resuelto",
    )))
    for incident in stale:
        if incident.fingerprint not in active_fingerprints:
            incident.status = "Resuelto"
            incident.resolved_by = "sistema-v0.45"
            incident.resolved_at = now
            touched += 1
    return touched


def run_deployment_rehearsal(
    session: Session,
    organization_id: int,
    performed_by: str,
    strict: bool = False,
    notes: str = "",
) -> DeploymentRehearsal:
    started_clock = time.perf_counter()
    started_at = datetime.now(UTC)
    checks = production_checks(strict=strict)
    critical = [item for item in checks if item["critical"]]
    passed = sum(1 for item in critical if item["ok"])
    score = round((passed / max(1, len(critical))) * 100)
    blockers = [item for item in checks if item["critical"] and not item["ok"]]
    warnings = [item for item in checks if not item["critical"] and not item["ok"]]
    status = "Aprobado" if not blockers else ("Parcial" if not strict else "Bloqueado")
    rehearsal = DeploymentRehearsal(
        organization_id=organization_id,
        status=status,
        score=score,
        strict_mode=strict,
        environment=settings.environment,
        database_backend=settings.database_backend,
        storage_backend=settings.storage_backend,
        checks_json=json.dumps(checks, ensure_ascii=False),
        blockers_json=json.dumps(blockers, ensure_ascii=False),
        warnings_json=json.dumps(warnings, ensure_ascii=False),
        notes=notes.strip(),
        performed_by=performed_by,
        started_at=started_at,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - started_clock) * 1000),
    )
    session.add(rehearsal)
    sync_incidents(session, organization_id, checks)
    session.flush()
    return rehearsal


def readiness_summary(session: Session, organization_id: int) -> dict[str, object]:
    latest = session.scalar(select(DeploymentRehearsal).where(
        DeploymentRehearsal.organization_id == organization_id,
    ).order_by(DeploymentRehearsal.started_at.desc()))
    open_incidents = list(session.scalars(select(OperationalIncident).where(
        OperationalIncident.organization_id == organization_id,
        OperationalIncident.status != "Resuelto",
    ).order_by(OperationalIncident.severity, OperationalIncident.last_seen_at.desc())))
    checks = production_checks(strict=True)
    blockers = [item for item in checks if item["critical"] and not item["ok"]]
    return {
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "latest": latest,
        "open_incidents": open_incidents,
    }


def upsert_external_alert(
    session: Session,
    organization_id: int,
    title: str,
    detail: str,
    severity: str = "Alta",
    source: str = "Alertmanager",
) -> OperationalIncident:
    now = datetime.now(UTC)
    fingerprint = _fingerprint(source + ":" + title, detail)
    incident = session.scalar(select(OperationalIncident).where(
        OperationalIncident.organization_id == organization_id,
        OperationalIncident.fingerprint == fingerprint,
    ))
    if incident:
        incident.occurrence_count += 1
        incident.last_seen_at = now
        incident.detail = detail
        incident.severity = severity
        if incident.status == "Resuelto":
            incident.status = "Abierto"
            incident.resolved_at = None
            incident.resolved_by = ""
    else:
        incident = OperationalIncident(
            organization_id=organization_id,
            fingerprint=fingerprint,
            title=title[:220],
            severity=severity[:30],
            status="Abierto",
            source=source[:80],
            detail=detail,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(incident)
    session.flush()
    return incident
