from __future__ import annotations

import json
from pathlib import Path
from datetime import UTC, datetime

from fastapi import Body, Depends, Form, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import DeploymentRehearsal, OperationalIncident, ReleaseCertification, RestoreDrill, add_audit, get_db
from .deployment_readiness import readiness_summary, run_deployment_rehearsal, upsert_external_alert
from .observability import metrics
from .release_certification import latest_certification, resolve_certification_artifact, run_release_certification
from .production_readiness import production_profile, sanitized_environment_template
from .security import secure_secret_matches
from .operations import (
    create_backup,
    diagnostic_snapshot,
    list_backups,
    rehearse_backup_restore,
    resolve_backup,
    verify_backup_archive,
)


def register_operations_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
) -> None:
    @app.get("/operacion", response_class=HTMLResponse)
    def operations_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        snapshot = diagnostic_snapshot()
        backups = list_backups()
        organization_id = int(user["organization_id"])
        drills = list(session.scalars(
            select(RestoreDrill)
            .where(RestoreDrill.organization_id == organization_id)
            .order_by(RestoreDrill.started_at.desc())
            .limit(20)
        ))
        deployments = list(session.scalars(
            select(DeploymentRehearsal)
            .where(DeploymentRehearsal.organization_id == organization_id)
            .order_by(DeploymentRehearsal.started_at.desc())
            .limit(20)
        ))
        certifications = list(session.scalars(
            select(ReleaseCertification)
            .where(ReleaseCertification.organization_id == organization_id)
            .order_by(ReleaseCertification.started_at.desc())
            .limit(20)
        ))
        incidents = list(session.scalars(
            select(OperationalIncident)
            .where(OperationalIncident.organization_id == organization_id)
            .order_by(OperationalIncident.status, OperationalIncident.last_seen_at.desc())
            .limit(30)
        ))
        readiness = readiness_summary(session, organization_id)
        production = production_profile(snapshot, readiness, backups)
        return templates.TemplateResponse(
            request=request,
            name="operations.html",
            context=common_context(
                request,
                session,
                user,
                "operations",
                snapshot=snapshot,
                backups=backups,
                restore_drills=drills,
                deployment_rehearsals=deployments,
                release_certifications=certifications,
                operational_incidents=incidents,
                readiness=readiness,
                metrics_snapshot=metrics.snapshot(),
                app_settings=settings,
                production_profile=production,
            ),
        )

    @app.post("/operacion/respaldos")
    def operations_backup(
        request: Request,
        label: str = Form("manual"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        try:
            result = create_backup(created_by=str(user["email"]), label=label)
        except (OSError, RuntimeError, TimeoutError) as exc:
            set_flash(request, f"No fue posible generar el respaldo: {exc}", "error")
            return RedirectResponse("/operacion", status_code=303)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "RESPALDAR",
            "Sistema",
            str(result["name"]),
            detail=f"SHA-256 {result['sha256']} · firmado={result.get('signed')} · réplica={result.get('offsite_key') or 'no'}",
        )
        session.commit()
        message = f"Respaldo generado: {result['name']}"
        if result.get("signed"):
            message += " · manifiesto firmado"
        if result.get("offsite_key"):
            message += " · réplica externa confirmada"
        elif result.get("offsite_error"):
            message += f" · réplica pendiente: {result['offsite_error']}"
        set_flash(request, message)
        return RedirectResponse("/operacion", status_code=303)

    @app.get("/operacion/respaldos/{name}")
    def operations_backup_download(name: str, user: dict = Depends(require_user)):
        ensure_capability(user, "manage_operations")
        try:
            path = resolve_backup(name)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Respaldo no encontrado") from exc
        return FileResponse(path, media_type="application/zip", filename=path.name)

    @app.post("/operacion/respaldos/{name}/verificar")
    def operations_backup_verify(
        name: str,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        try:
            path = resolve_backup(name)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Respaldo no encontrado") from exc
        result = verify_backup_archive(path)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "VERIFICAR",
            "Respaldo",
            name,
            detail=f"Integridad {'correcta' if result['ok'] else 'fallida'} · SHA-256 {result.get('sha256', '')}",
        )
        session.commit()
        set_flash(
            request,
            "El respaldo superó la verificación de integridad."
            if result["ok"]
            else "El respaldo presenta inconsistencias: " + "; ".join(result["issues"]),
            "success" if result["ok"] else "error",
        )
        return RedirectResponse("/operacion", status_code=303)

    @app.post("/operacion/respaldos/{name}/ensayar")
    def operations_backup_rehearse(
        name: str,
        request: Request,
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        try:
            path = resolve_backup(name)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Respaldo no encontrado") from exc

        started = datetime.now(UTC)
        result = rehearse_backup_restore(path)
        drill = RestoreDrill(
            organization_id=int(user["organization_id"]),
            backup_name=name,
            backup_sha256=str(result.get("backup_sha256", "")),
            application_version=str(result.get("application_version", "")),
            database_backend=str(result.get("database_backend", "")),
            status=str(result.get("status", "Fallido")),
            integrity_result=str(result.get("integrity_result", "")),
            table_count=int(result.get("table_count", 0) or 0),
            record_summary_json=json.dumps(result.get("record_summary", {}), ensure_ascii=False, sort_keys=True),
            checks_json=json.dumps(result.get("checks", {}), ensure_ascii=False, sort_keys=True),
            notes=(notes.strip() + ("\n" if notes.strip() and result.get("issues") else "") + "; ".join(result.get("issues", []))).strip(),
            performed_by=str(user["email"]),
            started_at=started,
            completed_at=datetime.now(UTC),
            duration_ms=int(result.get("duration_ms", 0) or 0),
        )
        session.add(drill)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "ENSAYAR_RESTAURACION",
            "Respaldo",
            name,
            detail=f"Estado {drill.status} · integridad {drill.integrity_result} · {drill.table_count} tablas · SHA-256 {drill.backup_sha256}",
        )
        session.commit()
        if result.get("ok"):
            set_flash(request, "Ensayo aprobado: el respaldo fue restaurado y validado en un entorno aislado.")
        else:
            set_flash(
                request,
                "El ensayo no fue aprobado: " + ("; ".join(result.get("issues", [])) or "revisa los controles registrados."),
                "error",
            )
        return RedirectResponse("/operacion#restauracion", status_code=303)

    @app.post("/operacion/despliegue/ensayar")
    def operations_deployment_rehearse(
        request: Request,
        strict_mode: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        strict = strict_mode.strip().lower() in {"1", "true", "on", "si", "sí"}
        result = run_deployment_rehearsal(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            strict=strict,
            notes=notes,
        )
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "ENSAYAR_DESPLIEGUE",
            "Sistema",
            f"Ensayo #{result.id}",
            detail=f"Estado {result.status} · puntaje {result.score}% · modo {'estricto' if strict else 'local'}",
        )
        session.commit()
        set_flash(
            request,
            f"Ensayo {result.status.lower()}: puntaje {result.score}%." + (" Revisa los bloqueos críticos." if result.status != "Aprobado" else ""),
            "success" if result.status == "Aprobado" else "warning",
        )
        return RedirectResponse("/operacion#despliegue-controlado", status_code=303)

    @app.post("/operacion/certificacion/ejecutar")
    def operations_release_certify(
        request: Request,
        strict_mode: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        strict = strict_mode.strip().lower() in {"1", "true", "on", "si", "sí"}
        certification = run_release_certification(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            strict=strict,
            notes=notes,
        )
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "CERTIFICAR_VERSION",
            "Sistema",
            f"Certificación #{certification.id}",
            detail=(
                f"Estado {certification.status} · alcance {certification.scope} · "
                f"hash {certification.certificate_hash}"
            ),
        )
        session.commit()
        set_flash(
            request,
            (
                "Versión certificada para producción y evidencia replicada."
                if certification.production_approved
                else (
                    "Validación local completada. No equivale a certificación productiva."
                    if certification.status == "Validación local"
                    else "La certificación quedó bloqueada. Revisa las evidencias y dependencias pendientes."
                )
            ),
            "success" if certification.production_approved or certification.status == "Validación local" else "warning",
        )
        return RedirectResponse("/operacion#certificacion", status_code=303)

    @app.get("/operacion/certificaciones/{name}")
    def operations_release_certificate_download(
        name: str,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        certification = session.scalar(select(ReleaseCertification).where(
            ReleaseCertification.organization_id == int(user["organization_id"]),
            ReleaseCertification.artifact_name == Path(name).name,
        ))
        if not certification:
            raise HTTPException(404, "Certificación no encontrada")
        try:
            path = resolve_certification_artifact(certification.artifact_name)
        except FileNotFoundError as exc:
            raise HTTPException(404, "El paquete de evidencia no está disponible localmente") from exc
        return FileResponse(path, media_type="application/zip", filename=path.name)

    @app.get("/api/operacion/certificacion")
    def operations_release_certification_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        certification = latest_certification(session, int(user["organization_id"]))
        if certification is None:
            return {"available": False, "production_approved": False}
        return {
            "available": True,
            "id": certification.id,
            "version": certification.application_version,
            "scope": certification.scope,
            "status": certification.status,
            "production_approved": certification.production_approved,
            "certificate_hash": certification.certificate_hash,
            "artifact_name": certification.artifact_name,
            "artifact_sha256": certification.artifact_sha256,
            "external_artifact_key": certification.external_artifact_key,
            "started_at": certification.started_at.isoformat(),
        }

    @app.post("/operacion/incidentes/{incident_id}/reconocer")
    def operations_incident_acknowledge(
        incident_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        incident = session.scalar(select(OperationalIncident).where(
            OperationalIncident.id == incident_id,
            OperationalIncident.organization_id == int(user["organization_id"]),
        ))
        if not incident:
            raise HTTPException(404, "Incidente no encontrado")
        incident.status = "Reconocido"
        incident.acknowledged_by = str(user["email"])
        incident.acknowledged_at = datetime.now(UTC)
        session.commit()
        set_flash(request, "Incidente reconocido.")
        return RedirectResponse("/operacion#incidentes", status_code=303)

    @app.post("/operacion/incidentes/{incident_id}/resolver")
    def operations_incident_resolve(
        incident_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        incident = session.scalar(select(OperationalIncident).where(
            OperationalIncident.id == incident_id,
            OperationalIncident.organization_id == int(user["organization_id"]),
        ))
        if not incident:
            raise HTTPException(404, "Incidente no encontrado")
        incident.status = "Resuelto"
        incident.resolved_by = str(user["email"])
        incident.resolved_at = datetime.now(UTC)
        session.commit()
        set_flash(request, "Incidente marcado como resuelto.")
        return RedirectResponse("/operacion#incidentes", status_code=303)

    @app.get("/api/operacion/preparacion")
    def operations_readiness_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_operations")
        summary = readiness_summary(session, int(user["organization_id"]))
        latest = summary["latest"]
        snapshot = diagnostic_snapshot()
        backups = list_backups()
        profile = production_profile(snapshot, summary, backups)
        return {
            "ready": summary["ready"],
            "blockers": summary["blockers"],
            "checks": summary["checks"],
            "production_profile": profile,
            "open_incidents": len(summary["open_incidents"]),
            "latest": None if latest is None else {
                "id": latest.id,
                "status": latest.status,
                "score": latest.score,
                "strict_mode": latest.strict_mode,
                "started_at": latest.started_at.isoformat(),
            },
        }


    @app.get("/operacion/configuracion/plantilla", response_class=PlainTextResponse)
    def operations_environment_template(user: dict = Depends(require_user)):
        ensure_capability(user, "manage_operations")
        return PlainTextResponse(
            sanitized_environment_template(),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="calculatuhuella.env.production.template"'},
        )


    @app.post("/api/operacion/alertas")
    def operations_alert_webhook(
        payload: dict = Body(...),
        x_alert_secret: str = Header(""),
        authorization: str = Header(""),
        session: Session = Depends(get_db),
    ):
        supplied = x_alert_secret or authorization.removeprefix("Bearer ").strip()
        if not secure_secret_matches(supplied, settings.alert_webhook_secret):
            raise HTTPException(401, "Secreto de alertas inválido")
        alerts = payload.get("alerts") if isinstance(payload.get("alerts"), list) else []
        first_alert = alerts[0] if alerts else {}
        labels = first_alert.get("labels", {}) if isinstance(first_alert, dict) else {}
        annotations = first_alert.get("annotations", {}) if isinstance(first_alert, dict) else {}
        organization_id = int(payload.get("organization_id") or settings.alert_organization_id or 0)
        if organization_id <= 0:
            raise HTTPException(400, "organization_id o ALERT_ORGANIZATION_ID es obligatorio")
        title = str(payload.get("title") or payload.get("alertname") or labels.get("alertname") or annotations.get("summary") or "Alerta operativa")
        detail = str(payload.get("detail") or payload.get("description") or annotations.get("description") or json.dumps(payload, ensure_ascii=False))
        severity = str(payload.get("severity") or labels.get("severity") or "Alta")
        source = str(payload.get("source") or "Alertmanager")
        incident = upsert_external_alert(session, organization_id, title, detail, severity, source)
        alert_status = str(payload.get("status") or first_alert.get("status") or "").lower()
        if alert_status == "resolved":
            incident.status = "Resuelto"
            incident.resolved_by = "alertmanager"
            incident.resolved_at = datetime.now(UTC)
        add_audit(session, organization_id, "alertmanager", "ALERTA", "Incidente", incident.title, detail=incident.detail)
        session.commit()
        return {"ok": True, "incident_id": incident.id, "status": incident.status, "occurrences": incident.occurrence_count}

    @app.get("/metrics", response_class=PlainTextResponse)
    def prometheus_metrics(request: Request):
        token = settings.metrics_token
        supplied = request.headers.get("authorization", "")
        if token and not secure_secret_matches(supplied.removeprefix("Bearer ").strip(), token):
            raise HTTPException(401, "Token de métricas inválido")
        if settings.is_production and not token:
            raise HTTPException(503, "METRICS_TOKEN no configurado")
        return PlainTextResponse(metrics.prometheus(settings.version, settings.environment), media_type="text/plain; version=0.0.4")

