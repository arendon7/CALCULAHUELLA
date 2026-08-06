#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${CTH_PYTHON_BIN:-$ROOT/.venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
  echo "No se encontró el entorno Python instalado en $ROOT/.venv."
  echo "Ejecuta primero INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command."
  exit 2
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cth-audit.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

export APP_ENV=test
export SESSION_SECRET="auditoria-local-temporal-v100final"
export DATABASE_URL="sqlite+pysqlite:///$TMP_DIR/auditoria.sqlite3"
export INSTANCE_DIR="$TMP_DIR/instance"
export SEED_DEMO=true
export OPEN_BROWSER=0
export CSRF_ENABLED=true
export SCHEDULER_ENABLED=false
export STRUCTURED_LOGGING=false
export DEPLOYMENT_STRICT=false

cd "$ROOT"

echo "============================================================"
echo "   CALCULA TU HUELLA V1.0.0 · AUDITORÍA LOCAL COMPLETA"
echo "============================================================"

echo "[1/7] Compilando Python..."
"$PYTHON" -m compileall -q app scripts tests run.py

echo "[2/7] Validando scripts macOS y shell..."
find . -type f \( -name '*.sh' -o -name '*.command' \) -not -path './.venv/*' -print0 \
  | xargs -0 -n1 bash -n

echo "[3/7] Aplicando migraciones en una base temporal..."
"$PYTHON" -m alembic upgrade head >/dev/null

echo "[4/7] Compilando plantillas Jinja..."
"$PYTHON" - <<'PY'
from app.main import templates
names = sorted(templates.env.list_templates())
for name in names:
    templates.env.get_template(name)
print(f"Plantillas compiladas: {len(names)}")
PY

echo "[5/7] Verificando inventario y archivos prohibidos..."
"$PYTHON" scripts/build_release_inventory.py . \
  --csv "$TMP_DIR/source_inventory.csv" \
  --summary "$TMP_DIR/tree_summary.json" \
  --strict

echo "[6/7] Ejecutando suite integral reproducible..."
TEST_COUNT=$("$PYTHON" -m pytest --collect-only -q | awk '/tests collected/{print $1}' | tail -n 1)
if ! [[ "$TEST_COUNT" =~ ^[0-9]+$ ]]; then
  echo "No fue posible determinar el número de pruebas."
  exit 3
fi
START_SECONDS=$("$PYTHON" - <<'PY'
import time
print(time.monotonic())
PY
)
"$PYTHON" -m pytest -q
END_SECONDS=$("$PYTHON" - <<'PY'
import time
print(time.monotonic())
PY
)
DURATION=$("$PYTHON" - "$START_SECONDS" "$END_SECONDS" <<'PY'
import sys
print(round(float(sys.argv[2]) - float(sys.argv[1]), 3))
PY
)

echo "[7/7] Registrando evidencia verificable..."
"$PYTHON" scripts/validate_release_candidate.py \
  --record-passed \
  --test-count "$TEST_COUNT" \
  --duration-seconds "$DURATION" \
  > "$TMP_DIR/final_validation.json"
cat "$TMP_DIR/final_validation.json"

echo
echo "AUDITORÍA APROBADA: $TEST_COUNT pruebas, migraciones, plantillas, scripts, seguridad y estructura verificadas en ${DURATION}s."
