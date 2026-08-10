from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import ENGINE
from app.operations import (
    RESTORE_COUNT_TABLES,
    RESTORE_REQUIRED_TABLES,
    create_backup,
    verify_backup_archive,
)
from app.tenant_integrity import audit_chain_integrity, audit_tenant_integrity


def _safe_pg_url(raw_url: str):
    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("La base objetivo del gate debe ser PostgreSQL.")
    return url


def _pg_environment(url) -> dict[str, str]:
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = str(url.password)
    return environment


def _cli_database_url(url) -> str:
    return url.set(password=None, drivername="postgresql").render_as_string(hide_password=False)


def _table_counts(engine) -> dict[str, int]:
    table_names = set(inspect(engine).get_table_names())
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in RESTORE_COUNT_TABLES:
            if table in table_names:
                quoted = '"' + table.replace('"', '""') + '"'
                counts[table] = int(connection.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar() or 0)
    return counts


def run_gate() -> dict[str, object]:
    started_at = datetime.now(UTC)
    evidence_path = Path(os.environ.get("CONTINUITY_EVIDENCE_PATH", "postgres-restore-evidence.json"))
    target_url_raw = os.environ.get("POSTGRES_RESTORE_DATABASE_URL", "").strip()
    if settings.database_backend != "PostgreSQL":
        raise RuntimeError("DATABASE_URL del gate debe usar PostgreSQL.")
    if not target_url_raw:
        raise RuntimeError("POSTGRES_RESTORE_DATABASE_URL es obligatorio.")
    if len(settings.backup_signing_secret) < 32:
        raise RuntimeError("BACKUP_SIGNING_SECRET debe tener al menos 32 caracteres para certificar continuidad.")

    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        raise RuntimeError("pg_restore no está disponible.")

    target_url = _safe_pg_url(target_url_raw)
    target_engine = create_engine(target_url_raw, pool_pre_ping=True)
    result: dict[str, object] = {
        "ok": False,
        "started_at": started_at.isoformat(),
        "source_backend": settings.database_backend,
        "target_database": target_url.database or "",
        "checks": {},
        "issues": [],
    }
    checks: dict[str, bool] = result["checks"]  # type: ignore[assignment]
    issues: list[str] = result["issues"]  # type: ignore[assignment]

    backup = create_backup(created_by="v2-product-readiness", label="postgres-restore-gate")
    archive_path = Path(backup["path"])
    result["backup"] = {
        "name": backup["name"],
        "sha256": backup["sha256"],
        "size": backup["size"],
        "signed": backup["signed"],
    }
    archive_check = verify_backup_archive(archive_path)
    result["archive_verification"] = {
        "ok": archive_check.get("ok"),
        "signature_valid": archive_check.get("signature_valid"),
        "payloads_checked": archive_check.get("payloads_checked"),
        "issues": archive_check.get("issues", []),
    }
    checks["archive"] = bool(archive_check.get("ok"))
    checks["signature"] = archive_check.get("signature_valid") is True
    if not checks["archive"] or not checks["signature"]:
        issues.extend(str(item) for item in archive_check.get("issues", []))
        if not checks["signature"]:
            issues.append("La firma HMAC del backup no pudo certificarse.")

    manifest = dict(archive_check.get("manifest") or {})
    checks["postgres_manifest"] = str(manifest.get("database_backend", "")).lower() == "postgresql"
    database_file = str(manifest.get("database_file", ""))
    checks["pgdump_declared"] = database_file.endswith(".pgdump")

    if not all((checks["archive"], checks["signature"], checks["postgres_manifest"], checks["pgdump_declared"])):
        result["completed_at"] = datetime.now(UTC).isoformat()
        evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return result

    source_counts = _table_counts(ENGINE)
    result["source_counts"] = source_counts

    with tempfile.TemporaryDirectory(prefix="cth_pg_restore_gate_") as temp_name:
        temp_dir = Path(temp_name).resolve()
        dump_path = (temp_dir / Path(database_file).name).resolve()
        if dump_path.parent != temp_dir:
            raise RuntimeError("Ruta insegura para el dump PostgreSQL.")
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(database_file) as source, dump_path.open("wb") as target:
                shutil.copyfileobj(source, target)

        completed = subprocess.run(
            [
                pg_restore,
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                _cli_database_url(target_url),
                str(dump_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=_pg_environment(target_url),
        )
        result["pg_restore"] = {
            "returncode": completed.returncode,
            "stderr": completed.stderr[-4000:],
        }
        checks["restore_command"] = completed.returncode == 0
        if completed.returncode != 0:
            issues.append(completed.stderr.strip() or "pg_restore falló sin detalle.")

    try:
        table_names = set(inspect(target_engine).get_table_names())
        missing_tables = sorted(RESTORE_REQUIRED_TABLES - table_names)
        result["restored_table_count"] = len(table_names)
        result["missing_required_tables"] = missing_tables
        checks["required_tables"] = not missing_tables
        if missing_tables:
            issues.append("Faltan tablas requeridas: " + ", ".join(missing_tables))

        target_counts = _table_counts(target_engine)
        result["target_counts"] = target_counts
        checks["record_counts"] = source_counts == target_counts
        if not checks["record_counts"]:
            issues.append("Los conteos críticos del origen y la restauración no coinciden.")

        RestoredSession = sessionmaker(bind=target_engine, expire_on_commit=False, future=True)
        with RestoredSession() as session:
            tenant_result = audit_tenant_integrity(session)
            audit_result = audit_chain_integrity(session)
            organization_count = int(session.execute(text("SELECT COUNT(*) FROM organizations")).scalar() or 0)
            audit_event_count = int(session.execute(text("SELECT COUNT(*) FROM audit_events")).scalar() or 0)
        result["tenant_integrity"] = tenant_result
        result["audit_chain"] = audit_result
        result["organization_count"] = organization_count
        result["audit_event_count"] = audit_event_count
        checks["tenant_integrity"] = bool(tenant_result.get("ok"))
        checks["audit_chain"] = bool(audit_result.get("ok"))
        checks["non_empty_source"] = organization_count > 0 and audit_event_count > 0
        if not checks["tenant_integrity"]:
            issues.append(f"Integridad multiempresa falló: {tenant_result.get('critical_issue_count', 0)} inconsistencias críticas.")
        if not checks["audit_chain"]:
            issues.append(f"Cadena de auditoría falló: {audit_result.get('failure_count', 0)} inconsistencias.")
        if not checks["non_empty_source"]:
            issues.append("La restauración no contiene organizaciones y eventos de auditoría suficientes para un drill significativo.")
    finally:
        target_engine.dispose()

    result["ok"] = all(checks.values()) and not issues
    result["completed_at"] = datetime.now(UTC).isoformat()
    result["status"] = "Aprobado" if result["ok"] else "Fallido"
    evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return result


def main() -> int:
    try:
        result = run_gate()
    except Exception as exc:
        evidence_path = Path(os.environ.get("CONTINUITY_EVIDENCE_PATH", "postgres-restore-evidence.json"))
        result = {
            "ok": False,
            "status": "Fallido",
            "completed_at": datetime.now(UTC).isoformat(),
            "issues": [f"{type(exc).__name__}: {exc}"],
        }
        evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
