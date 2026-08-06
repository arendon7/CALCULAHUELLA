from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
ROOT = _PROJECT_ROOT

from sqlalchemy import select
from app.database import Organization, SessionLocal, init_db
from app.deployment_readiness import readiness_summary
from app.operations import diagnostic_snapshot, list_backups
from app.production_readiness import production_profile

if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        organization_id = session.scalar(select(Organization.id).order_by(Organization.id)) or 0
        readiness = readiness_summary(session, int(organization_id)) if organization_id else {"checks": [], "blockers": [], "open_incidents": [], "latest": None, "ready": False}
        payload = production_profile(diagnostic_snapshot(), readiness, list_backups())
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if payload["ready"] else 1)
