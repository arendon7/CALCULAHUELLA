#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="${1:-$ROOT/../calcula_tu_huella_v0_27_mac}"
SOURCE_DB="$SOURCE_DIR/instance/calculatuhuella_v027.db"
TARGET_DB="$ROOT/instance/calculatuhuella_v028.db"
source "$ROOT/scripts/runtime_python.sh"
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"
mkdir -p "$ROOT/instance"
if [ ! -f "$SOURCE_DB" ]; then
  echo "No se encontró la base V0.27 en: $SOURCE_DB"
  echo "Puedes indicar la carpeta anterior: ./migrate_from_v027.sh /ruta/calcula_tu_huella_v0_27_mac"
  exit 1
fi
STAMP="$(date +%Y%m%d_%H%M%S)"
if [ -f "$TARGET_DB" ]; then cp "$TARGET_DB" "$ROOT/instance/calculatuhuella_v028_pre_migration_${STAMP}.db"; fi
cp "$SOURCE_DB" "$TARGET_DB"
export APP_ENV=local SEED_DEMO=true
"$PY" -m alembic upgrade head
"$PY" - <<'PY'
from app.database import init_db
from app.operations import verify_audit_integrity
init_db()
result = verify_audit_integrity()
if not result["ok"]:
    raise SystemExit(f"La cadena de auditoría no superó la verificación: {result}")
print(f"Migración V0.27 → V0.28 completada. {result['checked']} eventos de auditoría verificados.")
PY
