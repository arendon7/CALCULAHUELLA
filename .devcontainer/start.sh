#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p instance

PID_FILE="instance/codespaces.pid"
LOG_FILE="instance/codespaces.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" || true
    sleep 1
  fi
fi

forwarding_domain="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  preview_host="${CODESPACE_NAME}-8765.${forwarding_domain}"
  export PUBLIC_BASE_URL="https://${preview_host}"
  export TRUSTED_HOSTS="${preview_host},localhost,127.0.0.1,testserver"
else
  export PUBLIC_BASE_URL="http://127.0.0.1:8765"
  export TRUSTED_HOSTS="localhost,127.0.0.1,testserver"
fi

export APP_ENV=local
export SESSION_SECRET="codespaces-preview-only-change-before-production"
export SESSION_HTTPS_ONLY=true
export DATABASE_URL="sqlite+pysqlite:///./instance/codespaces.sqlite3"
export SEED_DEMO=true
export OPEN_BROWSER=0
export HOST=0.0.0.0
export PORT=8765
export STORAGE_BACKEND=local
export EMAIL_BACKEND=file
export PAYMENT_BACKEND=demo
export SCHEDULER_ENABLED=false
export CSRF_ENABLED=true
export STRUCTURED_LOGGING=true
export AUDIT_CHAIN_ENABLED=true
export DEPLOYMENT_STRICT=false

.venv/bin/python -m alembic upgrade head >>"$LOG_FILE" 2>&1
nohup .venv/bin/python run.py >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

for attempt in {1..40}; do
  if curl -fsS http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
    echo "Calcula tu Huella disponible en el puerto 8765."
    echo "Credenciales demo: consultor@calculatuhuella.local / Demo2026!"
    exit 0
  fi
  sleep 1
done

echo "La vista previa no respondió. Revisa $LOG_FILE" >&2
exit 1
