from __future__ import annotations

import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import settings


def _stage(code: str, name: str, description: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = [item for item in checks if not item["ok"] and item.get("critical", True)]
    warnings = [item for item in checks if not item["ok"] and not item.get("critical", True)]
    return {
        "code": code,
        "name": name,
        "description": description,
        "status": "Listo" if not blockers and not warnings else ("Bloqueado" if blockers else "Advertencia"),
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "next_action": blockers[0]["action"] if blockers else (warnings[0]["action"] if warnings else "Mantener evidencia y monitoreo vigente."),
    }


def _item(label: str, ok: bool, detail: str, action: str, critical: bool = True) -> dict[str, Any]:
    return {"label": label, "ok": bool(ok), "detail": detail, "action": action, "critical": critical}


def smtp_connectivity_probe(timeout: float = 3.0) -> dict[str, Any]:
    if settings.email_backend != "smtp":
        return {"ok": False, "detail": f"Backend actual: {settings.email_backend}", "tested": False}
    if not settings.smtp_host:
        return {"ok": False, "detail": "SMTP_HOST no configurado", "tested": False}
    try:
        with socket.create_connection((settings.smtp_host, settings.smtp_port), timeout=timeout):
            return {"ok": True, "detail": f"{settings.smtp_host}:{settings.smtp_port} acepta conexión TCP", "tested": True}
    except OSError as exc:
        return {"ok": False, "detail": str(exc), "tested": True}


def production_profile(snapshot: dict[str, Any], readiness: dict[str, Any], backups: list[dict[str, Any]]) -> dict[str, Any]:
    latest_backup = backups[0] if backups else None
    restore = snapshot.get("restore_drill", {})
    external_checks = {str(item.get("code")): item for item in readiness.get("checks", [])}
    smtp_probe = smtp_connectivity_probe()

    stages = [
        _stage("runtime", "Aplicación y ejecución", "Proceso web, trabajador y automatizaciones separados.", [
            _item("Entorno productivo", settings.is_production, settings.environment, "Definir APP_ENV=production."),
            _item("Automatizaciones activas", settings.scheduler_enabled, f"SCHEDULER_ENABLED={settings.scheduler_enabled}", "Activar el worker programado."),
            _item("URL pública HTTPS", settings.public_base_url.startswith("https://"), settings.public_base_url, "Configurar dominio y HTTPS."),
        ]),
        _stage("database", "Base de datos", "Persistencia transaccional y migraciones reproducibles.", [
            _item("PostgreSQL", snapshot.get("database_backend") == "PostgreSQL", str(snapshot.get("database_detail", "")), "Migrar a PostgreSQL administrado o al servicio del stack."),
            _item("Conectividad", bool(snapshot.get("database_ok")), str(snapshot.get("database_detail", "")), "Corregir credenciales, red o disponibilidad de la base."),
        ]),
        _stage("storage", "Documentos y evidencias", "Almacenamiento externo con inventario y protección contra pérdida.", [
            _item("Backend externo", settings.storage_backend in {"filesystem", "s3"}, settings.storage_backend, "Configurar filesystem persistente o S3-compatible."),
            _item("Lectura y escritura", bool(snapshot.get("storage_ok")), str(snapshot.get("storage_detail", "")), "Verificar credenciales y permisos de objetos."),
            _item("Versionado o inmutabilidad", settings.object_storage_versioning_confirmed, f"Confirmado={settings.object_storage_versioning_confirmed}", "Activar versionado, retención o bloqueo de objetos en el proveedor."),
        ]),
        _stage("communications", "Correo transaccional", "Entrega de invitaciones, alertas y notificaciones.", [
            _item("Backend SMTP", settings.email_backend == "smtp", settings.email_backend, "Configurar EMAIL_BACKEND=smtp."),
            _item("Host SMTP", bool(settings.smtp_host), settings.smtp_host or "Sin host", "Configurar SMTP_HOST y credenciales."),
            _item("Conectividad SMTP", bool(smtp_probe["ok"]), str(smtp_probe["detail"]), "Habilitar red y validar el servicio SMTP.", critical=settings.email_backend == "smtp"),
        ]),
        _stage("continuity", "Continuidad y respaldos", "Respaldo firmado, réplica externa y restauración ensayada.", [
            _item("Respaldo existente", latest_backup is not None, latest_backup["name"] if latest_backup else "Sin respaldo", "Generar un respaldo antes de publicar."),
            _item("Firma HMAC", len(settings.backup_signing_secret) >= 32, "Configurada" if settings.backup_signing_secret else "No configurada", "Definir BACKUP_SIGNING_SECRET con al menos 32 caracteres."),
            _item("Réplica externa", settings.backup_offsite_enabled, f"Prefijo: {settings.backup_storage_prefix or 'sin definir'}", "Activar BACKUP_OFFSITE_ENABLED y separar el destino."),
            _item("Ensayo vigente", bool(restore.get("ok")), str(restore.get("status", "Sin ensayo")), f"Ejecutar restauración al menos cada {settings.restore_drill_max_age_days} días."),
        ]),
        _stage("security", "Seguridad y trazabilidad", "Sesiones, CSRF, secretos y auditoría verificable.", [
            _item("Cookie HTTPS", settings.session_https_only, f"SESSION_HTTPS_ONLY={settings.session_https_only}", "Activar cookies exclusivas de HTTPS."),
            _item("CSRF", settings.csrf_enabled, f"CSRF_ENABLED={settings.csrf_enabled}", "Mantener CSRF activo."),
            _item("Secreto de sesión", len(settings.session_secret) >= 32 and "change-in-production" not in settings.session_secret, "Longitud segura" if len(settings.session_secret) >= 32 else "Insuficiente", "Generar SESSION_SECRET aleatorio."),
            _item("Cadena de auditoría", bool(snapshot.get("audit_integrity", {}).get("ok")), f"{snapshot.get('audit_integrity', {}).get('checked', 0)} eventos", "Resolver cualquier ruptura de la cadena."),
        ]),
        _stage("observability", "Observabilidad e incidentes", "Métricas, alertas y tableros externos comprobables.", [
            _item("Token de métricas", bool(settings.metrics_token), "Configurado" if settings.metrics_token else "Ausente", "Definir METRICS_TOKEN."),
            _item("Webhook de alertas", bool(settings.alert_webhook_secret), "Configurado" if settings.alert_webhook_secret else "Ausente", "Definir ALERT_WEBHOOK_SECRET."),
            _item("Prometheus", bool(external_checks.get("prometheus_service", {}).get("ok")), str(external_checks.get("prometheus_service", {}).get("detail", "No comprobado")), "Conectar Prometheus con /metrics."),
            _item("Alertmanager", bool(external_checks.get("alertmanager_service", {}).get("ok")), str(external_checks.get("alertmanager_service", {}).get("detail", "No comprobado")), "Conectar Alertmanager al webhook autenticado."),
            _item("Grafana", bool(external_checks.get("grafana_service", {}).get("ok")), str(external_checks.get("grafana_service", {}).get("detail", "No comprobado")), "Configurar tablero y acceso administrativo."),
        ]),
    ]
    blockers = [check for stage in stages for check in stage["blockers"]]
    completed = sum(1 for stage in stages if stage["ready"])
    score = round(100 * sum(sum(1 for c in stage["checks"] if c["ok"]) for stage in stages) / max(1, sum(len(stage["checks"]) for stage in stages)))
    return {
        "version": settings.version,
        "generated_at": datetime.now(UTC).isoformat(),
        "ready": not blockers,
        "score": score,
        "completed_stages": completed,
        "total_stages": len(stages),
        "stages": stages,
        "blockers": blockers,
        "next_action": blockers[0]["action"] if blockers else "Ejecutar certificación estricta y conservar el paquete de evidencia.",
    }


def sanitized_environment_template() -> str:
    """Generate a production template without copying runtime secrets."""
    values = {
        "APP_ENV": "production",
        "SESSION_SECRET": "GENERAR_SECRETO_ALEATORIO_DE_48_BYTES",
        "SESSION_HTTPS_ONLY": "true",
        "DATABASE_URL": "postgresql+psycopg://USUARIO:CONTRASENA@HOST:5432/calculatuhuella",
        "PUBLIC_BASE_URL": "https://huella.ejemplo.com",
        "TRUSTED_HOSTS": "huella.ejemplo.com",
        "SEED_DEMO": "false",
        "MAX_UPLOAD_MB": "25",
        "MAX_REQUEST_MB": "30",
        "SLOW_REQUEST_SECONDS": "1.0",
        "METRICS_MAX_SERIES": "1000",
        "BOOTSTRAP_ADMIN_EMAIL": "admin@ejemplo.com",
        "BOOTSTRAP_ADMIN_PASSWORD": "GENERAR_CONTRASENA_SEGURA",
        "STORAGE_BACKEND": "s3",
        "S3_BUCKET": "calculatuhuella-documentos",
        "S3_ENDPOINT_URL": "https://s3.proveedor.example",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "CONFIGURAR_EN_GESTOR_DE_SECRETOS",
        "S3_SECRET_KEY": "CONFIGURAR_EN_GESTOR_DE_SECRETOS",
        "OBJECT_STORAGE_VERSIONING_CONFIRMED": "true",
        "BACKUP_RETENTION": "14",
        "BACKUP_SIGNING_SECRET": "GENERAR_SECRETO_ALEATORIO_DE_48_BYTES",
        "BACKUP_OFFSITE_ENABLED": "true",
        "BACKUP_STORAGE_PREFIX": "system-backups",
        "RESTORE_DRILL_MAX_AGE_DAYS": "90",
        "EMAIL_BACKEND": "smtp",
        "SMTP_HOST": "smtp.proveedor.example",
        "SMTP_PORT": "587",
        "SMTP_USER": "CONFIGURAR_EN_GESTOR_DE_SECRETOS",
        "SMTP_PASSWORD": "CONFIGURAR_EN_GESTOR_DE_SECRETOS",
        "SMTP_FROM": '"Calcula tu Huella <noreply@ejemplo.com>"',
        "SMTP_TLS": "true",
        "SCHEDULER_ENABLED": "true",
        "METRICS_TOKEN": "GENERAR_TOKEN_ALEATORIO",
        "ALERT_WEBHOOK_SECRET": "GENERAR_SECRETO_ALEATORIO",
        "ALERT_ORGANIZATION_ID": "1",
        "DEPLOYMENT_STRICT": "true",
        "CSRF_ENABLED": "true",
        "STRUCTURED_LOGGING": "true",
        "AUDIT_CHAIN_ENABLED": "true",
    }
    header = [
        "# Calcula tu Huella V1.0.0 · plantilla productiva sanitizada",
        "# No contiene secretos del entorno actual. Completa los valores en un gestor de secretos.",
        "",
    ]
    return "\n".join(header + [f"{key}={value}" for key, value in values.items()]) + "\n"
