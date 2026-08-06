#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

source scripts/python_selector.sh

DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$ROOT/instance}}"
TARGET_DB="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
export INSTANCE_DIR="$DATA_DIR"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$TARGET_DB}"
export APP_ENV="${APP_ENV:-local}"
export SEED_DEMO="${SEED_DEMO:-true}"

mkdir -p "$DATA_DIR" "$DATA_DIR/logs" "$DATA_DIR/backups" "$DATA_DIR/uploads" "$DATA_DIR/reports" "$DATA_DIR/certifications" "$DATA_DIR/import_staging" "$DATA_DIR/mail_outbox"

echo "Calcula tu Huella V1.0.0 · instalación para macOS"
echo "Arquitectura: $(uname -m)"
echo "Código: $ROOT"
echo "Datos persistentes: $DATA_DIR"

create_with_python() {
  local python_bin="$1"
  echo "Usando $python_bin (Python $(cth_python_version "$python_bin"))."
  if [ "${CTH_USE_SYSTEM_SITE_PACKAGES:-0}" = "1" ]; then
    "$python_bin" -m venv --system-site-packages "$ROOT/.venv"
  else
    "$python_bin" -m venv "$ROOT/.venv"
  fi
}

if [ -d .venv ]; then
  if [ ! -x .venv/bin/python ] || ! cth_python_version_ok .venv/bin/python; then
    old_version="$(cth_python_version .venv/bin/python 2>/dev/null || true)"
    echo "El entorno local usa Python ${old_version:-incompatible}; se reconstruirá sin tocar los datos."
    rm -rf .venv
  fi
fi

if [ ! -d .venv ]; then
  if cth_find_python; then
    create_with_python "$CTH_PYTHON_BIN"
  elif command -v conda >/dev/null 2>&1; then
    echo "Creando automáticamente un entorno Python 3.12 con Conda..."
    conda create --prefix "$ROOT/.venv" python=3.12 pip -y
  elif command -v brew >/dev/null 2>&1 && [ "${CTH_AUTO_INSTALL_PYTHON:-1}" = "1" ]; then
    echo "Python 3.11+ no está disponible. Homebrew instalará Python 3.12 automáticamente..."
    brew install python@3.12
    BREW_PY="$(brew --prefix python@3.12)/bin/python3.12"
    create_with_python "$BREW_PY"
  else
    cth_print_python_diagnostics
    echo
    echo "No se encontró Python 3.11 o superior."
    echo "La aplicación puede instalarlo automáticamente cuando Homebrew esté disponible."
    echo "Alternativa: instala Python 3.12 desde python.org y vuelve a abrir el instalador."
    if command -v open >/dev/null 2>&1; then
      open "https://www.python.org/downloads/macos/" >/dev/null 2>&1 || true
    fi
    exit 1
  fi
fi

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No se encontró el Python del entorno local: $PY"
  exit 1
fi

if ! "$PY" - <<'PYCODE'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PYCODE
then
  echo "El entorno creado no tiene Python 3.11 o superior."
  exit 1
fi

"$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
if ! "$PY" -m pip install --upgrade pip setuptools wheel; then
  echo "Aviso: no fue posible actualizar pip/setuptools/wheel; se usarán las herramientas disponibles."
fi

if "$PY" - <<'PYCODE' >/dev/null 2>&1
import alembic, fastapi, jinja2, openpyxl, pydantic, reportlab, sqlalchemy, uvicorn
PYCODE
then
  echo "Las dependencias principales ya están disponibles."
else
  "$PY" -m pip install -r requirements.txt
fi

"$PY" - <<'PYCODE'
import alembic
import fastapi
import jinja2
import openpyxl
import pydantic
import reportlab
import sqlalchemy
import uvicorn
print("Dependencias principales verificadas.")
PYCODE

if [ ! -f "$TARGET_DB" ] && [ -n "${CTH_LEGACY_DB:-}" ] && [ -f "$CTH_LEGACY_DB" ]; then
  echo "Migrando la base más reciente: $(basename "$CTH_LEGACY_DB")"
  "$PY" scripts/copy_sqlite_database.py "$CTH_LEGACY_DB" "$TARGET_DB"
fi

if [ -f "$TARGET_DB" ]; then
  STAMP="$(date +%Y%m%d_%H%M%S)"
  "$PY" scripts/copy_sqlite_database.py "$TARGET_DB" "$DATA_DIR/backups/pre_v0453_${STAMP}.db"
  "$PY" scripts/ensure_alembic_baseline.py "$TARGET_DB" "${CTH_LEGACY_DB:-$(basename "$TARGET_DB")}" 
fi

"$PY" -m alembic upgrade head
"$PY" - <<'PYCODE'
from app.database import init_db
init_db()
print("Base de datos V1.0.0 preparada con Alembic.")
PYCODE
"$PY" scripts/check_ready.py

echo
echo "Instalación completada con $($PY --version)."
echo "Base persistente: $TARGET_DB"
