from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import init_db  # noqa: E402
from app.operations import create_backup  # noqa: E402

parser = argparse.ArgumentParser(description="Genera un respaldo consistente de Calcula tu Huella.")
parser.add_argument("--label", default="cli")
args = parser.parse_args()
init_db()
result = create_backup(created_by="cli", label=args.label)
print(result["path"])
print(f"SHA-256: {result['sha256']}")
