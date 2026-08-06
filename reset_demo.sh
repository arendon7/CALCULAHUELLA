#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$INSTALL_ROOT/data}}"
DB_PATH="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"
if [ "${1:-}" != "--confirmar" ]; then
  echo "Esta operación reemplaza la base actual por datos demostrativos."
  echo "Ejecuta: ./reset_demo.sh --confirmar"
  exit 1
fi
mkdir -p "$DATA_DIR/backups"
if [ -f "$DB_PATH" ]; then
  "$PY" scripts/copy_sqlite_database.py "$DB_PATH" "$DATA_DIR/backups/pre_reset_demo_$(date +%Y%m%d_%H%M%S).db"
  rm -f "$DB_PATH"
fi
export INSTANCE_DIR="$DATA_DIR" DATABASE_URL="sqlite:///$DB_PATH" APP_ENV=local SEED_DEMO=true
"$PY" -m alembic upgrade head
"$PY" - <<'PYCODE'
from app.database import init_db
init_db()
print("Datos demostrativos V1.0.0 restaurados; el respaldo previo fue conservado.")
PYCODE
