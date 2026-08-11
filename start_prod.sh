#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"

export APP_ENV="${APP_ENV:-production}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8765}"
export OPEN_BROWSER=0

# La base transaccional y sus migraciones sí son requisitos de arranque y
# fallan cerrado antes de iniciar el proceso web.
"$PY" -m alembic upgrade head
"$PY" - <<'PYCODE'
from app.database import init_db
init_db()
print("Esquema e inicialización verificados.")
PYCODE

# No ejecutar probes de red u object storage antes de abrir el puerto. La
# disponibilidad estricta se expone después del bind en /api/ready;
# scripts/check_ready.py se conserva como auditoría explícita/manual.
exec "$PY" -m uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --no-access-log
