from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.automations import process_due_automations  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402

init_db()
print(f"Programador V{settings.version} iniciado. Intervalo: {settings.scheduler_interval_seconds} segundos")
while True:
    with SessionLocal() as session:
        result = process_due_automations(session)
        if result["executed"] or result["errors"]:
            print(result)
    time.sleep(max(15, settings.scheduler_interval_seconds))
