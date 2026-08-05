#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Calcula tu Huella requiere Python 3.11 o superior")
print(f"Python validado: {sys.version.split()[0]}")
PY

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt

mkdir -p instance/uploads instance/notifications instance/reports

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

.venv/bin/python -m alembic upgrade head

echo "Codespaces preparado. La aplicación se iniciará automáticamente en el puerto 8765."
