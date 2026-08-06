from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from app.config import INSTANCE_DIR
from app.database_transfer import DatabaseTransferError, database_inventory, transfer_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Migración transaccional SQLite → PostgreSQL")
    parser.add_argument("--source", default=f"sqlite:///{INSTANCE_DIR / 'calculatuhuella.db'}")
    parser.add_argument("--target", default=os.environ.get("POSTGRES_TARGET_URL", ""))
    parser.add_argument("--confirm", default="")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    if not args.target:
        print("POSTGRES_TARGET_URL o --target es obligatorio.")
        return 2
    plan = {"source": args.source, "target_backend": args.target.split(":", 1)[0], "tables": database_inventory(args.source)}
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if args.confirm != "MIGRAR":
        print("Operación cancelada. Usa --confirm MIGRAR después de revisar el plan.")
        return 2

    env = os.environ.copy()
    env["DATABASE_URL"] = args.target
    completed = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=False)
    if completed.returncode:
        print("No fue posible preparar el esquema PostgreSQL con Alembic.")
        return completed.returncode
    try:
        result = transfer_database(args.source, args.target)
    except DatabaseTransferError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, **result.as_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
