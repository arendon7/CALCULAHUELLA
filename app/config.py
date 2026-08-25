from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
INSTANCE_DIR = Path(os.environ.get("INSTANCE_DIR", PROJECT_DIR / "instance")).resolve()
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Calcula tu Huella"
    version: str = "1.0.0"
    environment: str = os.environ.get("APP_ENV", "local").strip().lower()
    database_url: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{INSTANCE_DIR / 'calculatuhuella.db'}",
    )
    session_secret: str = os.environ.get(
        "SESSION_SECRET",
        "local-demo-change-in-production-v030",
    )
    session_https_only: bool = env_bool("SESSION_HTTPS_ONLY", False)
    trusted_hosts: tuple[str, ...] = tuple(env_list("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver"))
    public_base_url: str = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    public_result_max_age_hours: int = int(os.environ.get("PUBLIC_RESULT_MAX_AGE_HOURS", "720"))
    max_upload_mb: int = int(os.environ.get("MAX_UPLOAD_MB", "10"))
    max_request_mb: int = int(os.environ.get("MAX_REQUEST_MB", "12"))
    slow_request_seconds: float = float(os.environ.get("SLOW_REQUEST_SECONDS", "1.0"))
    metrics_max_series: int = int(os.environ.get("METRICS_MAX_SERIES", "1000"))
    backup_retention: int = int(os.environ.get("BACKUP_RETENTION", "14"))
    backup_signing_secret: str = os.environ.get("BACKUP_SIGNING_SECRET", "")
    backup_offsite_enabled: bool = env_bool("BACKUP_OFFSITE_ENABLED", False)
    backup_storage_prefix: str = os.environ.get("BACKUP_STORAGE_PREFIX", "system-backups").strip().strip("/")
    object_storage_versioning_confirmed: bool = env_bool("OBJECT_STORAGE_VERSIONING_CONFIRMED", False)
    restore_drill_max_age_days: int = int(os.environ.get("RESTORE_DRILL_MAX_AGE_DAYS", "90"))
    login_attempts: int = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
    login_window_seconds: int = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))
    login_block_seconds: int = int(os.environ.get("LOGIN_BLOCK_SECONDS", "900"))
    seed_demo: bool = env_bool("SEED_DEMO", os.environ.get("APP_ENV", "local").strip().lower() != "production")
    bootstrap_admin_email: str = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    bootstrap_admin_password: str = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    bootstrap_organization: str = os.environ.get("BOOTSTRAP_ORGANIZATION", "Organización inicial")
    storage_backend: str = os.environ.get("STORAGE_BACKEND", "local").strip().lower()
    s3_bucket: str = os.environ.get("S3_BUCKET", "").strip()
    s3_endpoint_url: str = os.environ.get("S3_ENDPOINT_URL", "").strip()
    s3_region: str = os.environ.get("S3_REGION", "us-east-1").strip()
    s3_access_key: str = os.environ.get("S3_ACCESS_KEY", "").strip()
    s3_secret_key: str = os.environ.get("S3_SECRET_KEY", "").strip()
    s3_connect_timeout_seconds: float = float(os.environ.get("S3_CONNECT_TIMEOUT_SECONDS", "5"))
    s3_read_timeout_seconds: float = float(os.environ.get("S3_READ_TIMEOUT_SECONDS", "30"))
    s3_max_attempts: int = int(os.environ.get("S3_MAX_ATTEMPTS", "3"))
    external_storage_root: str = os.environ.get("EXTERNAL_STORAGE_ROOT", "").strip()
    metrics_token: str = os.environ.get("METRICS_TOKEN", "").strip()
    alert_webhook_secret: str = os.environ.get("ALERT_WEBHOOK_SECRET", "").strip()
    alert_organization_id: int = int(os.environ.get("ALERT_ORGANIZATION_ID", "0") or 0)
    deployment_strict: bool = env_bool("DEPLOYMENT_STRICT", False)
    object_storage_health_url: str = os.environ.get("OBJECT_STORAGE_HEALTH_URL", "").strip()
    prometheus_health_url: str = os.environ.get("PROMETHEUS_HEALTH_URL", "").strip()
    alertmanager_health_url: str = os.environ.get("ALERTMANAGER_HEALTH_URL", "").strip()
    grafana_health_url: str = os.environ.get("GRAFANA_HEALTH_URL", "").strip()
    external_probe_timeout_seconds: float = float(os.environ.get("EXTERNAL_PROBE_TIMEOUT_SECONDS", "3"))
    email_backend: str = os.environ.get("EMAIL_BACKEND", "file").strip().lower()
    smtp_host: str = os.environ.get("SMTP_HOST", "").strip()
    smtp_port: int = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user: str = os.environ.get("SMTP_USER", "").strip()
    smtp_password: str = os.environ.get("SMTP_PASSWORD", "")
    smtp_from: str = os.environ.get("SMTP_FROM", "Calcula tu Huella <noreply@localhost>")
    smtp_tls: bool = env_bool("SMTP_TLS", True)
    notification_batch_size: int = int(os.environ.get("NOTIFICATION_BATCH_SIZE", "50"))
    scheduler_enabled: bool = env_bool("SCHEDULER_ENABLED", True)
    scheduler_interval_seconds: int = int(os.environ.get("SCHEDULER_INTERVAL_SECONDS", "60"))
    payment_backend: str = os.environ.get("PAYMENT_BACKEND", "demo").strip().lower()
    payment_webhook_secret: str = os.environ.get("PAYMENT_WEBHOOK_SECRET", "")
    csrf_enabled: bool = env_bool("CSRF_ENABLED", True)
    structured_logging: bool = env_bool("STRUCTURED_LOGGING", True)
    audit_chain_enabled: bool = env_bool("AUDIT_CHAIN_ENABLED", True)
    rc_greenatics_pilot_approved: bool = env_bool("RC_GREENATICS_PILOT_APPROVED", False)
    rc_second_sector_pilot_approved: bool = env_bool("RC_SECOND_SECTOR_PILOT_APPROVED", False)
    rc_carlos_review_approved: bool = env_bool("RC_CARLOS_REVIEW_APPROVED", False)
    rc_windows_10_approved: bool = env_bool("RC_WINDOWS_10_APPROVED", False)
    rc_windows_11_approved: bool = env_bool("RC_WINDOWS_11_APPROVED", False)
    rc_security_review_approved: bool = env_bool("RC_SECURITY_REVIEW_APPROVED", False)
    rc_legal_review_approved: bool = env_bool("RC_LEGAL_REVIEW_APPROVED", False)
    final_methodology_internal_approved: bool = env_bool("FINAL_METHODOLOGY_INTERNAL_APPROVED", True)
    final_legal_internal_approved: bool = env_bool("FINAL_LEGAL_INTERNAL_APPROVED", True)
    final_greenatics_internal_pilot_approved: bool = env_bool("FINAL_GREENATICS_INTERNAL_PILOT_APPROVED", True)
    final_second_sector_internal_pilot_approved: bool = env_bool("FINAL_SECOND_SECTOR_INTERNAL_PILOT_APPROVED", True)
    final_infrastructure_approved: bool = env_bool("FINAL_INFRASTRUCTURE_APPROVED", False)
    legal_provider_name: str = os.environ.get("LEGAL_PROVIDER_NAME", "GREENATICS S.A.S.").strip()
    legal_provider_nit: str = os.environ.get("LEGAL_PROVIDER_NIT", "").strip()
    legal_notice_address: str = os.environ.get("LEGAL_NOTICE_ADDRESS", "").strip()
    legal_contact_email: str = os.environ.get("LEGAL_CONTACT_EMAIL", "").strip().lower()
    privacy_contact_email: str = os.environ.get("PRIVACY_CONTACT_EMAIL", "").strip().lower()
    legal_effective_date: str = os.environ.get("LEGAL_EFFECTIVE_DATE", "2026-08-05").strip()
    sla_monthly_availability_target: float = float(os.environ.get("SLA_MONTHLY_AVAILABILITY_TARGET", "99.5"))
    sla_rpo_hours: int = int(os.environ.get("SLA_RPO_HOURS", "24"))
    sla_rto_hours: int = int(os.environ.get("SLA_RTO_HOURS", "8"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_backend(self) -> str:
        if self.database_url.startswith("postgresql"):
            return "PostgreSQL"
        if self.database_url.startswith("sqlite"):
            return "SQLite"
        return self.database_url.split(":", 1)[0]

    def production_issues(self) -> list[str]:
        issues: list[str] = []
        if len(self.session_secret) < 32 or "change-in-production" in self.session_secret:
            issues.append("SESSION_SECRET debe ser aleatorio y tener al menos 32 caracteres.")
        if not self.session_https_only:
            issues.append("SESSION_HTTPS_ONLY debe estar activo detrás de HTTPS.")
        if self.database_backend != "PostgreSQL":
            issues.append("Para producción se recomienda PostgreSQL en lugar de SQLite.")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            issues.append("TRUSTED_HOSTS debe contener únicamente los dominios autorizados.")
        if not self.public_base_url.startswith("https://"):
            issues.append("PUBLIC_BASE_URL debe usar HTTPS.")
        if self.seed_demo:
            issues.append("SEED_DEMO debe estar desactivado en producción.")
        if self.max_request_mb < self.max_upload_mb:
            issues.append("MAX_REQUEST_MB debe ser igual o superior a MAX_UPLOAD_MB.")
        if self.max_request_mb > 100:
            issues.append("MAX_REQUEST_MB no debe superar 100 MB sin una justificación operativa documentada.")
        if self.slow_request_seconds <= 0:
            issues.append("SLOW_REQUEST_SECONDS debe ser mayor que cero.")
        if self.metrics_max_series < 100:
            issues.append("METRICS_MAX_SERIES debe ser al menos 100 para conservar visibilidad operativa.")
        if self.storage_backend == "s3" and not self.s3_bucket:
            issues.append("S3_BUCKET es obligatorio cuando STORAGE_BACKEND=s3.")
        if self.storage_backend == "s3" and self.s3_endpoint_url and (not self.s3_access_key or not self.s3_secret_key):
            issues.append("S3_ACCESS_KEY y S3_SECRET_KEY son obligatorios para endpoints S3 personalizados.")
        if bool(self.s3_access_key) != bool(self.s3_secret_key):
            issues.append("S3_ACCESS_KEY y S3_SECRET_KEY deben configurarse como pareja.")
        if self.s3_connect_timeout_seconds <= 0 or self.s3_read_timeout_seconds <= 0:
            issues.append("Los timeouts S3 deben ser mayores que cero.")
        if self.s3_max_attempts < 1:
            issues.append("S3_MAX_ATTEMPTS debe ser al menos 1.")
        if self.external_probe_timeout_seconds <= 0:
            issues.append("EXTERNAL_PROBE_TIMEOUT_SECONDS debe ser mayor que cero.")
        if self.storage_backend == "filesystem" and not self.external_storage_root:
            issues.append("EXTERNAL_STORAGE_ROOT es obligatorio cuando STORAGE_BACKEND=filesystem.")
        if self.storage_backend not in {"local", "filesystem", "s3"}:
            issues.append("STORAGE_BACKEND debe ser local, filesystem o s3.")
        if self.storage_backend == "local":
            issues.append("Producción requiere almacenamiento externo filesystem o S3-compatible.")
        if len(self.backup_signing_secret) < 32:
            issues.append("BACKUP_SIGNING_SECRET debe ser aleatorio y tener al menos 32 caracteres.")
        if not self.backup_offsite_enabled:
            issues.append("BACKUP_OFFSITE_ENABLED debe estar activo para replicar respaldos fuera del volumen de aplicación.")
        if not self.backup_storage_prefix:
            issues.append("BACKUP_STORAGE_PREFIX debe definir una ruta separada para respaldos.")
        if self.backup_retention < 7:
            issues.append("BACKUP_RETENTION debe conservar al menos 7 respaldos en producción.")
        if not self.object_storage_versioning_confirmed:
            issues.append("OBJECT_STORAGE_VERSIONING_CONFIRMED debe confirmar versionado o inmutabilidad del almacenamiento externo.")
        if not self.metrics_token:
            issues.append("METRICS_TOKEN debe configurarse para proteger las métricas productivas.")
        if not self.alert_webhook_secret:
            issues.append("ALERT_WEBHOOK_SECRET debe configurarse para autenticar alertas externas.")
        if self.alert_organization_id <= 0:
            issues.append("ALERT_ORGANIZATION_ID debe identificar la organización que recibirá alertas operativas.")
        for label, url in (
            ("OBJECT_STORAGE_HEALTH_URL", self.object_storage_health_url),
            ("PROMETHEUS_HEALTH_URL", self.prometheus_health_url),
            ("ALERTMANAGER_HEALTH_URL", self.alertmanager_health_url),
            ("GRAFANA_HEALTH_URL", self.grafana_health_url),
        ):
            if not url:
                issues.append(f"{label} debe configurarse para certificar el stack productivo.")
        if self.email_backend == "smtp" and not self.smtp_host:
            issues.append("SMTP_HOST es obligatorio cuando EMAIL_BACKEND=smtp.")
        if self.email_backend != "smtp":
            issues.append("EMAIL_BACKEND debe ser smtp para comunicaciones productivas.")
        if not self.scheduler_enabled:
            issues.append("SCHEDULER_ENABLED debe estar activo para automatizaciones, notificaciones y respaldos programados.")
        if self.payment_backend not in {"demo", "manual", "webhook"}:
            issues.append("PAYMENT_BACKEND debe ser demo, manual o webhook.")
        if self.payment_backend == "webhook" and not self.payment_webhook_secret:
            issues.append("PAYMENT_WEBHOOK_SECRET es obligatorio cuando PAYMENT_BACKEND=webhook.")
        if not self.csrf_enabled:
            issues.append("CSRF_ENABLED debe estar activo en producción.")
        if not self.structured_logging:
            issues.append("STRUCTURED_LOGGING debe estar activo para trazabilidad operativa.")
        if not self.audit_chain_enabled:
            issues.append("AUDIT_CHAIN_ENABLED debe estar activo para integridad de auditoría.")
        if not self.legal_provider_name:
            issues.append("LEGAL_PROVIDER_NAME debe identificar al proveedor contractual.")
        if not self.legal_provider_nit:
            issues.append("LEGAL_PROVIDER_NIT debe configurarse antes de publicación comercial.")
        if not self.legal_notice_address:
            issues.append("LEGAL_NOTICE_ADDRESS debe definir la dirección de notificaciones.")
        if "@" not in self.legal_contact_email:
            issues.append("LEGAL_CONTACT_EMAIL debe ser un correo válido.")
        if "@" not in self.privacy_contact_email:
            issues.append("PRIVACY_CONTACT_EMAIL debe ser un correo válido para consultas de titulares.")
        return issues


settings = Settings()
