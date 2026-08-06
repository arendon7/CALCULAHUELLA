from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    checks: list[dict[str, object]] = []

    def add(code: str, ok: bool, detail: str, critical: bool = True) -> None:
        checks.append({"code": code, "ok": bool(ok), "detail": detail, "critical": critical})

    version_ok = (3, 11) <= sys.version_info[:2] <= (3, 13)
    add("python_version", version_ok, platform.python_version())
    add("project_root", (ROOT / "app" / "main.py").is_file(), str(ROOT))
    add("requirements", (ROOT / "requirements.txt").is_file(), "requirements.txt presente")
    add("migrations", (ROOT / "alembic.ini").is_file() and (ROOT / "migrations").is_dir(), "Alembic presente")

    try:
        with tempfile.TemporaryDirectory(prefix="cth_preflight_", dir=ROOT) as temp_name:
            probe = Path(temp_name) / "probe.txt"
            probe.write_text("ok", encoding="utf-8")
            add("write_permissions", probe.read_text(encoding="utf-8") == "ok", "Escritura local disponible")
    except OSError as exc:
        add("write_permissions", False, str(exc))

    try:
        with tempfile.TemporaryDirectory(prefix="cth_sqlite_") as temp_name:
            db = Path(temp_name) / "probe.db"
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)")
            connection.execute("INSERT INTO probe(value) VALUES ('ok')")
            connection.commit()
            value = connection.execute("SELECT value FROM probe").fetchone()[0]
            connection.close()
            add("sqlite_runtime", value == "ok", sqlite3.sqlite_version)
    except sqlite3.DatabaseError as exc:
        add("sqlite_runtime", False, str(exc))

    executable = Path(sys.executable)
    add("python_executable", executable.is_file(), str(executable))
    add("free_space", shutil.disk_usage(ROOT).free >= 500 * 1024 * 1024, f"{shutil.disk_usage(ROOT).free // (1024 * 1024)} MB libres")

    os_name = platform.system()
    if os_name == "Darwin":
        add("mac_launcher", (ROOT / "1_INSTALAR_Y_ABRIR.command").is_file(), "Lanzador macOS", critical=False)
    elif os_name == "Windows":
        add("windows_launcher", (ROOT / "1_INSTALAR_Y_ABRIR.bat").is_file(), "Lanzador Windows", critical=False)
    else:
        add("native_platform", False, f"Entorno de validación {os_name}; no es una certificación física Mac/Windows.", critical=False)

    critical_failures = [item for item in checks if item["critical"] and not item["ok"]]
    payload = {
        "ok": not critical_failures,
        "status": "Aprobado" if not critical_failures else "Bloqueado",
        "generated_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "checks": checks,
        "critical_failures": critical_failures,
        "project_manifest": {
            "requirements_sha256": _sha256(ROOT / "requirements.txt") if (ROOT / "requirements.txt").is_file() else "",
            "main_sha256": _sha256(ROOT / "app" / "main.py") if (ROOT / "app" / "main.py").is_file() else "",
        },
    }
    evidence = ROOT / "release" / "platform_preflight.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**payload, "evidence": str(evidence)}, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
