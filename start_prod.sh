#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# El preview de Render tiene una PostgreSQL administrada y aislada declarada en
# render.yaml. Si alguien reemplaza DATABASE_URL manualmente por una URL externa,
# fallamos con un diagnóstico explícito antes de entrar a Alembic/SQLAlchemy.
if [[ "${APP_ENV:-production}" == "staging" \
  && "${RENDER_PREVIEW_DB_ONLY:-0}" == "1" \
  && "${DATABASE_URL:-}" == *"supabase.com"* ]]; then
  echo "ERROR: Render preview database drift detected." >&2
  echo "DATABASE_URL must come from calcula-tu-huella-preview-db in render.yaml." >&2
  echo "Sync the Render Blueprint instead of overriding DATABASE_URL manually." >&2
  exit 78
fi

# Proveedores administrados como Render suelen entregar connection strings
# PostgreSQL genéricos. El runtime productivo usa psycopg 3, por lo que normalizamos
# el esquema en el borde de despliegue sin alterar la configuración de desarrollo.
if [[ "${DATABASE_URL:-}" == postgresql://* ]]; then
  export DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}"
elif [[ "${DATABASE_URL:-}" == postgres://* ]]; then
  export DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}"
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
