#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "No se encontró $PYTHON_BIN. Instala Python 3.11 o superior." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Calcula tu Huella requiere Python 3.11 o superior.")
print(f"Python validado: {sys.version.split()[0]}")
PY

# GitHub Contents API y algunas descargas ZIP no conservan el bit ejecutable.
# Se normalizan únicamente los lanzadores propios del repositorio.
find "$PROJECT_ROOT" -maxdepth 1 -type f -name '*.command' -exec chmod u+x {} +
find "$PROJECT_ROOT/scripts" -type f \( -name '*.sh' -o -name '*.command' \) -exec chmod u+x {} +

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "No fue posible crear el entorno virtual." >&2
  exit 1
fi

"$VENV_PYTHON" -m pip install --upgrade pip
if [[ -f requirements-dev.txt ]]; then
  "$VENV_PYTHON" -m pip install -r requirements-dev.txt
else
  "$VENV_PYTHON" -m pip install -r requirements.txt
fi

if [[ ! -f .env.local ]]; then
  cp .env.local.example .env.local
  echo "Creado .env.local desde la configuración local de ejemplo."
fi

mkdir -p instance/uploads instance/notifications instance/reports

set -a
# shellcheck disable=SC1091
source .env.local
set +a

"$VENV_PYTHON" -m alembic upgrade head

echo
echo "Instalación local completada."
echo "Inicia la aplicación con: ./scripts/dev/run.sh"
echo "Recuperación de marca disponible: ./RECUPERAR_MARCA_MAESTRA_MAC.command"
