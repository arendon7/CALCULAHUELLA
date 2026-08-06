from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
ROOT = _PROJECT_ROOT

from app.production_readiness import sanitized_environment_template

if __name__ == "__main__":
    destination = Path(_sys.argv[1] if len(_sys.argv) > 1 else ROOT / ".env.production.template")
    destination.write_text(sanitized_environment_template(), encoding="utf-8")
    print(destination)
