from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import INSTANCE_DIR, settings
from app.operations import create_backup, rehearse_backup_restore, verify_backup_archive


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_member(archive: zipfile.ZipFile, member_name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member_name) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)
        target.flush()
        os.fsync(target.fileno())


def _validate_sqlite(path: Path) -> None:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            raise RuntimeError(f"PRAGMA integrity_check: {integrity}")
    finally:
        connection.close()


def _replace_database(staged_db: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_target = target.with_name(f".{target.name}.restore-{os.getpid()}.tmp")
    shutil.copy2(staged_db, temporary_target)
    with temporary_target.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary_target, target)


def _restore_directory(staged_root: Path, folder_name: str) -> int:
    source = staged_root / folder_name
    if not source.exists():
        return 0
    destination = INSTANCE_DIR / folder_name
    replacement = INSTANCE_DIR / f".{folder_name}.restore-{os.getpid()}"
    shutil.rmtree(replacement, ignore_errors=True)
    shutil.copytree(source, replacement)
    shutil.rmtree(destination, ignore_errors=True)
    shutil.move(str(replacement), str(destination))
    return sum(1 for item in destination.rglob("*") if item.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restaura de forma verificable un respaldo SQLite con la aplicación detenida."
    )
    parser.add_argument("archive")
    parser.add_argument("--confirm", action="store_true", help="Confirmación obligatoria de escritura")
    parser.add_argument("--dry-run", action="store_true", help="Validar sin modificar la instalación")
    parser.add_argument("--allow-version-mismatch", action="store_true")
    parser.add_argument("--skip-safety-backup", action="store_true")
    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        raise SystemExit("Operación bloqueada. Repite con --confirm o usa --dry-run.")
    if settings.database_backend != "SQLite":
        raise SystemExit("Este script solo restaura instalaciones SQLite.")

    archive_path = Path(args.archive).expanduser().resolve()
    if not archive_path.is_file():
        raise SystemExit(f"No existe el respaldo: {archive_path}")

    archive_check = verify_backup_archive(archive_path)
    if not archive_check.get("ok"):
        raise SystemExit("Respaldo rechazado: " + "; ".join(archive_check.get("issues", [])))
    manifest = dict(archive_check.get("manifest") or {})
    backup_version = str(manifest.get("version", ""))
    if backup_version != settings.version and not args.allow_version_mismatch:
        raise SystemExit(
            f"Versión incompatible: respaldo {backup_version or '(sin versión)'} / aplicación {settings.version}. "
            "Usa --allow-version-mismatch únicamente después de validar migraciones."
        )
    if str(manifest.get("database_backend", "")).lower() != "sqlite":
        raise SystemExit("El archivo no contiene un respaldo SQLite.")

    drill = rehearse_backup_restore(archive_path)
    if not drill.get("ok"):
        raise SystemExit("El ensayo aislado falló: " + "; ".join(drill.get("issues", [])))

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "mode": "dry-run",
            "archive": archive_path.name,
            "archive_sha256": archive_check.get("sha256"),
            "version": backup_version,
            "restore_drill": drill,
        }, ensure_ascii=False, indent=2, default=str))
        return 0

    target = Path(settings.database_url.removeprefix("sqlite:///"))
    safety_backup = None
    if target.exists() and target.stat().st_size and not args.skip_safety_backup:
        safety_backup = create_backup(created_by="restore-sqlite", label="pre-restauracion")

    restored_files: dict[str, int] = {"uploads": 0, "reports": 0}
    with tempfile.TemporaryDirectory(prefix="cth_restore_verified_") as temp_name:
        temp = Path(temp_name)
        database_file = str(manifest["database_file"])
        staged_db = temp / Path(database_file).name
        payload_root = temp / "payload"

        payload_names = {
            str(item.get("name", ""))
            for item in manifest.get("payloads", [])
            if str(item.get("name", ""))
        }
        with zipfile.ZipFile(archive_path) as bundle:
            _copy_member(bundle, database_file, staged_db)
            for member_name in sorted(payload_names):
                if member_name == database_file or member_name == "external_storage_inventory.json":
                    continue
                if not member_name.startswith(("uploads/", "reports/")):
                    continue
                _copy_member(bundle, member_name, payload_root / member_name)

        _validate_sqlite(staged_db)
        _replace_database(staged_db, target)
        _validate_sqlite(target)
        for folder_name in restored_files:
            restored_files[folder_name] = _restore_directory(payload_root, folder_name)

    receipt_dir = INSTANCE_DIR / "restorations"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "status": "Restauración completada",
        "completed_at": datetime.now(UTC).isoformat(),
        "application_version": settings.version,
        "backup_version": backup_version,
        "archive": archive_path.name,
        "archive_sha256": str(archive_check.get("sha256", "")),
        "target_database": str(target),
        "target_database_sha256": _sha256(target),
        "safety_backup": {
            "name": safety_backup["name"],
            "sha256": safety_backup["sha256"],
        } if safety_backup else None,
        "restored_files": restored_files,
        "restore_drill": drill,
    }
    receipt_path = receipt_dir / f"restauracion_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"ok": True, "receipt": str(receipt_path), **receipt}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
