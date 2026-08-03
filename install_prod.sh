#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi
PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --upgrade pip setuptools wheel
"$PY" -m pip install -r requirements-prod.txt
"$PY" -m alembic upgrade head
"$PY" - <<'PYCODE'
from app.database import init_db
init_db()
print("Esquema V0.22 preparado con Alembic.")
PYCODE
"$PY" scripts/check_ready.py
echo "Instalación productiva completada. Ejecuta ./start_prod.sh"
