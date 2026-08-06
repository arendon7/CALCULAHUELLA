from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import init_db  # noqa: E402
from app.operations import diagnostic_snapshot  # noqa: E402

init_db()
snapshot = diagnostic_snapshot()
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
raise SystemExit(0 if snapshot["status"] == "ready" else 1)
