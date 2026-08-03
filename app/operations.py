from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from .config import INSTANCE_DIR, settings
from .database import ENGINE
from .storage import storage
from .security import security_state_snapshot

BACKUP_DIR = INSTANCE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_ready() -> tuple[bool, str]:
    try:
        with ENGINE.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, f"{settings.database_backend} disponible"
    except Exception as exc:  # pragma: no cover - mensaje operativo
        return False, str(exc)


def storage_ready() -> tuple[bool, str]:
    result = storage.diagnostics()
    return bool(result["ok"]), f"{result['backend']}: {result['detail']}"


def diagnostic_snapshot() -> dict[str, object]:
    db_ok, db_detail = database_ready()
    storage_ok, storage_detail = storage_ready()
    issues = settings.production_issues()
    admin_ok = False
    if db_ok:
        try:
            with ENGINE.connect() as connection:
                admin_ok = bool(connection.execute(text("SELECT COUNT(*) FROM app_users WHERE role = 'Administrador' AND active = true")).scalar())
        except Exception:
            admin_ok = False
    if settings.is_production and not admin_ok:
        issues.append("La instalación necesita al menos un administrador activo; configura BOOTSTRAP_ADMIN_EMAIL y BOOTSTRAP_ADMIN_PASSWORD.")
    production_ready = db_ok and storage_ok and admin_ok and not issues
    operational_ready = db_ok and storage_ok and (not settings.is_production or production_ready)
    audit_integrity = verify_audit_integrity() if db_ok and settings.audit_chain_enabled else {"ok": not settings.audit_chain_enabled, "checked": 0, "failure_count": 0}
    security_state = security_state_snapshot() if db_ok else {"ok": False, "active_blocks": 0, "tracked_keys": 0}
    log_state = structured_log_snapshot()
    restore_state = restore_drill_snapshot()
    if settings.is_production and not audit_integrity.get("ok"):
        issues.append("La cadena de auditoría presenta inconsistencias.")
    if settings.is_production and not log_state.get("ok"):
        issues.append("El registro estructurado no está disponible.")
    if settings.is_production and not restore_state.get("ok"):
        issues.append("Debe existir un ensayo de restauración aprobado y vigente (máximo 90 días).")
    production_ready = production_ready and bool(audit_integrity.get("ok")) and bool(log_state.get("ok")) and (not settings.is_production or bool(restore_state.get("ok")))
    operational_ready = operational_ready and bool(audit_integrity.get("ok"))
    return {
        "status": "ready" if operational_ready else "degraded",
        "database_ok": db_ok,
        "database_detail": db_detail,
        "storage_ok": storage_ok,
        "storage_detail": storage_detail,
        "admin_ok": admin_ok,
        "environment": settings.environment,
        "database_backend": settings.database_backend,
        "storage_backend": settings.storage_backend,
        "email_backend": settings.email_backend,
        "https_cookie": settings.session_https_only,
        "trusted_hosts": list(settings.trusted_hosts),
        "public_base_url": settings.public_base_url,
        "production_issues": issues,
        "production_ready": production_ready,
        "csrf_enabled": settings.csrf_enabled,
        "audit_chain_enabled": settings.audit_chain_enabled,
        "audit_integrity": audit_integrity,
        "security_state": security_state,
        "structured_log": log_state,
        "restore_drill": restore_state,
    }


def _copy_sqlite_database(destination: Path, timeout_seconds: int = 20) -> None:
    """Create a consistent SQLite backup without waiting indefinitely on locks."""
    import time

    url = settings.database_url
    source_path = Path(url.removeprefix("sqlite:///"))
    source = sqlite3.connect(source_path, timeout=5)
    target = sqlite3.connect(destination, timeout=5)
    deadline = time.monotonic() + max(timeout_seconds, 1)

    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError(
                "La base permaneció bloqueada durante el respaldo. "
                "Cierra cargas o ediciones activas e inténtalo nuevamente."
            )

    try:
        source.execute("PRAGMA busy_timeout = 5000")
        target.execute("PRAGMA busy_timeout = 5000")
        source.backup(target, pages=256, progress=progress, sleep=0.05)
    finally:
        target.close()
        source.close()


def _dump_postgres(destination: Path) -> None:
    executable = shutil.which("pg_dump")
    if not executable:
        raise RuntimeError("No se encontró pg_dump. Instala PostgreSQL client tools.")
    url = make_url(settings.database_url)
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    safe_url = url.set(password=None, drivername="postgresql")
    subprocess.run(
        [executable, "--dbname", safe_url.render_as_string(hide_password=False), "--format=custom", "--file", str(destination)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )


def create_backup(created_by: str = "sistema", label: str = "manual") -> dict[str, object]:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    safe_label = "".join(ch for ch in label.lower().replace(" ", "-") if ch.isalnum() or ch in "-_")[:30] or "manual"
    archive = BACKUP_DIR / f"calculatuhuella_{stamp}_{safe_label}.zip"

    with tempfile.TemporaryDirectory(prefix="cth_backup_") as temp_name:
        temp_dir = Path(temp_name)
        if settings.database_backend == "SQLite":
            db_dump = temp_dir / "database.sqlite3"
            _copy_sqlite_database(db_dump)
        elif settings.database_backend == "PostgreSQL":
            db_dump = temp_dir / "database.pgdump"
            _dump_postgres(db_dump)
        else:
            raise RuntimeError(f"Backend no soportado para respaldo: {settings.database_backend}")

        manifest = {
            "application": settings.app_name,
            "version": settings.version,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "label": safe_label,
            "database_backend": settings.database_backend,
        "storage_backend": settings.storage_backend,
        "email_backend": settings.email_backend,
            "database_file": db_dump.name,
        }
        (temp_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(db_dump, db_dump.name)
            bundle.write(temp_dir / "manifest.json", "manifest.json")
            for folder_name in ("uploads", "reports"):
                folder = INSTANCE_DIR / folder_name
                if folder.exists():
                    for path in folder.rglob("*"):
                        if path.is_file():
                            bundle.write(path, str(path.relative_to(INSTANCE_DIR)))

    result = {
        "name": archive.name,
        "path": archive,
        "size": archive.stat().st_size,
        "sha256": _sha256(archive),
        "created_at": datetime.now(UTC),
    }
    prune_backups(settings.backup_retention)
    return result


def list_backups() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for path in sorted(BACKUP_DIR.glob("calculatuhuella_*.zip"), key=lambda item: item.stat().st_mtime, reverse=True):
        results.append({
            "name": path.name,
            "size": path.stat().st_size,
            "created_at": datetime.fromtimestamp(path.stat().st_mtime, UTC),
            "sha256": _sha256(path),
        })
    return results


def prune_backups(retention: int) -> None:
    backups = sorted(BACKUP_DIR.glob("calculatuhuella_*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in backups[max(1, retention):]:
        path.unlink(missing_ok=True)


def resolve_backup(name: str) -> Path:
    candidate = (BACKUP_DIR / Path(name).name).resolve()
    if candidate.parent != BACKUP_DIR.resolve() or not candidate.exists():
        raise FileNotFoundError(name)
    return candidate


def verify_audit_integrity() -> dict[str, object]:
    """Recompute the per-organization audit hash chain."""
    from sqlalchemy import select
    from .database import AuditEvent, SessionLocal, audit_event_digest

    checked = 0
    failures: list[dict[str, object]] = []
    with SessionLocal() as session:
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
                previous_hash = expected
    return {
        "ok": not failures,
        "checked": checked,
        "failures": failures[:20],
        "failure_count": len(failures),
    }


def structured_log_snapshot() -> dict[str, object]:
    path = INSTANCE_DIR / "logs" / "application.jsonl"
    if not path.exists():
        return {"ok": True, "path": str(path), "size": 0, "records": 0}
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            records = sum(1 for _ in handle)
        return {"ok": True, "path": str(path), "size": size, "records": records}
    except OSError as exc:
        return {"ok": False, "path": str(path), "size": 0, "records": 0, "detail": str(exc)}


def verify_backup_archive(path: Path) -> dict[str, object]:
    """Validate ZIP integrity, safe paths and mandatory manifest/database members."""
    result: dict[str, object] = {"ok": False, "name": path.name, "sha256": "", "members": 0, "issues": []}
    issues: list[str] = []
    try:
        result["sha256"] = _sha256(path)
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                issues.append(f"Miembro dañado: {bad}")
            names = archive.namelist()
            result["members"] = len(names)
            for name in names:
                parts = Path(name).parts
                if name.startswith(("/", "\\")) or ".." in parts:
                    issues.append(f"Ruta insegura: {name}")
            if "manifest.json" not in names:
                issues.append("Falta manifest.json")
            else:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                result["manifest"] = manifest
                db_file = manifest.get("database_file", "")
                if not db_file or db_file not in names:
                    issues.append("El archivo de base de datos declarado no existe")
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        issues.append(str(exc))
    result["issues"] = issues
    result["ok"] = not issues
    return result

RESTORE_REQUIRED_TABLES = {
    "organizations",
    "app_users",
    "inventories",
    "emission_sources",
    "activity_data",
    "emission_calculations",
    "evidence_documents",
    "audit_events",
}
RESTORE_COUNT_TABLES = (
    "organizations",
    "app_users",
    "inventories",
    "emission_sources",
    "activity_data",
    "emission_calculations",
    "evidence_documents",
    "audit_events",
)


def rehearse_backup_restore(path: Path) -> dict[str, object]:
    """Restore a backup into an isolated temporary directory and validate it.

    This function never writes to the live database or persistent storage. It is
    intentionally conservative: a drill is approved only when archive integrity,
    manifest consistency and database-level checks all pass.
    """
    import time

    started = time.perf_counter()
    archive_check = verify_backup_archive(path)
    result: dict[str, object] = {
        "ok": False,
        "status": "Fallido",
        "backup_name": path.name,
        "backup_sha256": archive_check.get("sha256", ""),
        "application_version": "",
        "database_backend": "",
        "integrity_result": "No ejecutado",
        "table_count": 0,
        "record_summary": {},
        "checks": {
            "archive": bool(archive_check.get("ok")),
            "safe_paths": not any("Ruta insegura" in item for item in archive_check.get("issues", [])),
            "manifest": bool(archive_check.get("manifest")),
            "database": False,
            "required_tables": False,
        },
        "issues": list(archive_check.get("issues", [])),
        "duration_ms": 0,
    }
    if not archive_check.get("ok"):
        result["duration_ms"] = round((time.perf_counter() - started) * 1000)
        return result

    manifest = dict(archive_check.get("manifest") or {})
    result["application_version"] = str(manifest.get("version", ""))
    result["database_backend"] = str(manifest.get("database_backend", ""))
    database_file = str(manifest.get("database_file", ""))

    with tempfile.TemporaryDirectory(prefix="cth_restore_drill_") as temp_name:
        temp_dir = Path(temp_name)
        try:
            with zipfile.ZipFile(path) as archive:
                member = archive.getinfo(database_file)
                destination = (temp_dir / Path(database_file).name).resolve()
                if destination.parent != temp_dir.resolve():
                    raise RuntimeError("La ruta declarada para la base no es segura.")
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

            backend = str(manifest.get("database_backend", "")).lower()
            if backend == "sqlite" or destination.suffix in {".sqlite", ".sqlite3", ".db"}:
                connection = sqlite3.connect(f"file:{destination}?mode=ro", uri=True)
                try:
                    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
                    tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                        )
                    }
                    missing = sorted(RESTORE_REQUIRED_TABLES - tables)
                    summary: dict[str, int] = {}
                    for table in RESTORE_COUNT_TABLES:
                        if table in tables:
                            quoted = '"' + table.replace('"', '""') + '"'
                            summary[table] = int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
                    result["integrity_result"] = integrity
                    result["table_count"] = len(tables)
                    result["record_summary"] = summary
                    result["checks"]["database"] = integrity.lower() == "ok"
                    result["checks"]["required_tables"] = not missing
                    if missing:
                        result["issues"].append("Faltan tablas requeridas: " + ", ".join(missing))
                    if integrity.lower() != "ok":
                        result["issues"].append(f"PRAGMA integrity_check: {integrity}")
                finally:
                    connection.close()
            elif backend == "postgresql" or destination.suffix == ".pgdump":
                executable = shutil.which("pg_restore")
                if not executable:
                    result["status"] = "Parcial"
                    result["issues"].append("El archivo PostgreSQL está íntegro, pero pg_restore no está disponible para listar el dump.")
                else:
                    completed = subprocess.run(
                        [executable, "--list", str(destination)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    result["integrity_result"] = "pg_restore --list"
                    result["checks"]["database"] = completed.returncode == 0
                    result["checks"]["required_tables"] = completed.returncode == 0
                    if completed.returncode != 0:
                        result["issues"].append(completed.stderr.strip() or "pg_restore no pudo leer el dump.")
            else:
                result["issues"].append(f"Backend no soportado en ensayo automático: {manifest.get('database_backend', '')}")
        except (OSError, KeyError, sqlite3.DatabaseError, RuntimeError, zipfile.BadZipFile) as exc:
            result["issues"].append(str(exc))

    all_checks = all(bool(value) for value in result["checks"].values())
    if all_checks and not result["issues"]:
        result["ok"] = True
        result["status"] = "Aprobado"
    elif result["status"] != "Parcial":
        result["status"] = "Fallido"
    result["duration_ms"] = round((time.perf_counter() - started) * 1000)
    return result


def restore_drill_snapshot(max_age_days: int = 90) -> dict[str, object]:
    """Return continuity readiness based on persisted restore drills."""
    from sqlalchemy import select
    from .database import RestoreDrill, SessionLocal

    with SessionLocal() as session:
        latest = session.scalar(select(RestoreDrill).order_by(RestoreDrill.started_at.desc()))
        latest_success = session.scalar(
            select(RestoreDrill)
            .where(RestoreDrill.status == "Aprobado")
            .order_by(RestoreDrill.completed_at.desc(), RestoreDrill.started_at.desc())
        )
    if not latest_success:
        return {
            "ok": False,
            "status": "Sin ensayo aprobado",
            "latest": latest,
            "latest_success": None,
            "age_days": None,
            "max_age_days": max_age_days,
        }
    completed = latest_success.completed_at or latest_success.started_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=UTC)
    age_days = max(0, (datetime.now(UTC) - completed).days)
    return {
        "ok": age_days <= max_age_days,
        "status": "Vigente" if age_days <= max_age_days else "Vencido",
        "latest": latest,
        "latest_success": latest_success,
        "age_days": age_days,
        "max_age_days": max_age_days,
    }
