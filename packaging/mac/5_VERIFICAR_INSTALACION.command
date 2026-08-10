#!/bin/bash
set -euo pipefail

INSTALL_ROOT="$HOME/Library/Application Support/CalculaTuHuellaDemoFull"
CODE_DIR="$INSTALL_ROOT/current"
DATA_DIR="$INSTALL_ROOT/data"
RUNTIME_DIR="$INSTALL_ROOT/runtime"
PY="$RUNTIME_DIR/python/bin/python3"

test -x "$PY" || { echo "Python portable: FALTA"; read -r; exit 1; }
test -d "$RUNTIME_DIR/vendor" || { echo "Dependencias: FALTAN"; read -r; exit 1; }
test -f "$CODE_DIR/run.py" || { echo "Código: FALTA"; read -r; exit 1; }
test -f "$CODE_DIR/requirements-lock.txt" || { echo "Lock de dependencias: FALTA"; read -r; exit 1; }
test -f "$INSTALL_ROOT/BUILD_PROVENANCE.json" || { echo "Trazabilidad de build: FALTA"; read -r; exit 1; }

export PYTHONPATH="$RUNTIME_DIR/vendor:$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR"
export DATABASE_URL="sqlite:///$DATA_DIR/calculatuhuella.db"
export APP_ENV=local
export SEED_DEMO=true
export SCHEDULER_ENABLED=0
export STRUCTURED_LOGGING=0

cd "$CODE_DIR"
"$PY" -m alembic current
"$PY" scripts/check_ready.py
"$PY" - <<'PY'
import json
from pathlib import Path

path = Path.home() / "Library/Application Support/CalculaTuHuellaDemoFull/BUILD_PROVENANCE.json"
data = json.loads(path.read_text(encoding="utf-8"))
print(f"Commit instalado: {data['source_commit']}")
print(f"Runtime: CPython {data['python']['version']} · {data['python']['release_tag']}")
PY

echo "Instalación verificada correctamente."
