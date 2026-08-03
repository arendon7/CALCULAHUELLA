from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import INSTANCE_DIR, settings  # noqa: E402

parser = argparse.ArgumentParser(description="Restaura un respaldo SQLite. Ejecutar con la aplicación detenida.")
parser.add_argument("archive")
parser.add_argument("--confirm", action="store_true")
args = parser.parse_args()
if not args.confirm:
    raise SystemExit("Operación bloqueada. Repite el comando con --confirm.")
if settings.database_backend != "SQLite":
    raise SystemExit("Este script solo restaura instalaciones SQLite.")
archive = Path(args.archive).expanduser().resolve()
with tempfile.TemporaryDirectory(prefix="cth_restore_") as temp_name:
    temp = Path(temp_name)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(temp)
    manifest = json.loads((temp / "manifest.json").read_text(encoding="utf-8"))
    source_db = temp / manifest["database_file"]
    connection = sqlite3.connect(source_db)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise SystemExit(f"Respaldo inválido: {result}")
    finally:
        connection.close()
    target = Path(settings.database_url.removeprefix("sqlite:///"))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, target)
    for folder_name in ("uploads", "reports"):
        source = temp / folder_name
        if source.exists():
            target_folder = INSTANCE_DIR / folder_name
            shutil.rmtree(target_folder, ignore_errors=True)
            shutil.copytree(source, target_folder)
print(f"Restauración completada desde {archive.name}")
