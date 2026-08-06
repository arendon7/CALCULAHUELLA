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

# En despliegues gratuitos, una verificación externa de S3 puede tardar más
# que la ventana de detección de puerto de Render. En modo estricto se exige
# el diagnóstico completo antes de servir; en demo se ejecuta en segundo plano
# y Uvicorn abre el puerto inmediatamente.
if [ "${DEPLOYMENT_STRICT:-false}" = "true" ]; then
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
