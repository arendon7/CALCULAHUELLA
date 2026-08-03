#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"
DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$ROOT/instance}}"
TARGET_DB="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
SOURCE_DB="${1:-}"
if [ -z "$SOURCE_DB" ]; then
  SOURCE_DB="$(find "$ROOT/.." -maxdepth 4 -type f -name 'calculatuhuella_v028.db' 2>/dev/null | head -n 1 || true)"
fi
if [ -z "$SOURCE_DB" ] || [ ! -f "$SOURCE_DB" ]; then
  echo "No se encontró calculatuhuella_v028.db. Indica la ruta como primer argumento."
  exit 1
fi
mkdir -p "$DATA_DIR/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
if [ -f "$TARGET_DB" ]; then "$PY" scripts/copy_sqlite_database.py "$TARGET_DB" "$DATA_DIR/backups/calculatuhuella_pre_migration_${STAMP}.db"; fi
"$PY" scripts/copy_sqlite_database.py "$SOURCE_DB" "$TARGET_DB"
"$PY" scripts/ensure_alembic_baseline.py "$TARGET_DB" "v028"
export INSTANCE_DIR="$DATA_DIR" DATABASE_URL="sqlite:///$TARGET_DB" APP_ENV=local SEED_DEMO=true
"$PY" -m alembic upgrade head
"$PY" - <<'PY'
from app.database import init_db
init_db()
print("Migración V0.28 → V0.45 completada. La base original no fue modificada.")
PY
