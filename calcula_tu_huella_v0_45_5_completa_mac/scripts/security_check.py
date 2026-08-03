from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import json
from pathlib import Path

from app.config import INSTANCE_DIR, settings
from app.database import init_db
from app.operations import diagnostic_snapshot, list_backups, verify_backup_archive

init_db()
snapshot = diagnostic_snapshot()
backups = list_backups()
backup_result = None
if backups:
    backup_path = Path(backups[0]["path"]) if "path" in backups[0] else INSTANCE_DIR / "backups" / str(backups[0]["name"])
    backup_result = verify_backup_archive(backup_path)

result = {
    "version": settings.version,
    "status": snapshot["status"],
    "csrf_enabled": snapshot["csrf_enabled"],
    "audit_integrity": snapshot["audit_integrity"],
    "security_state": snapshot["security_state"],
    "structured_log": snapshot["structured_log"],
    "latest_backup": backup_result,
    "production_issues": snapshot["production_issues"],
}
print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
raise SystemExit(0 if snapshot["status"] == "ready" and snapshot["audit_integrity"]["ok"] else 1)
