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

"$PY" -m alembic upgrade head
"$PY" - <<'PYCODE'
from app.database import init_db
init_db()
print("Esquema e inicialización verificados.", flush=True)
PYCODE

# Render debe abrir el puerto antes de depender de servicios externos.
# DEPLOYMENT_STRICT conserva la puerta estricta en otros entornos.
# En Render, la comprobación previa solo vuelve a ser bloqueante si se
# habilita explícitamente RENDER_STRICT_STARTUP=true.
STRICT_STARTUP="${DEPLOYMENT_STRICT:-false}"
if [ "${RENDER:-false}" = "true" ] && [ "${RENDER_STRICT_STARTUP:-false}" != "true" ]; then
  STRICT_STARTUP=false
fi

if [ "$STRICT_STARTUP" = "true" ]; then
  "$PY" scripts/check_ready.py
else
  (
    "$PY" scripts/check_ready.py \
      && echo "Diagnóstico de disponibilidad completado." \
      || echo "Advertencia: diagnóstico externo degradado; revisa /api/ready."
  ) &
fi

exec "$PY" -m uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --no-access-log
