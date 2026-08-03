#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
CODE_DIR="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"
DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
CHECK_ROOT="$ROOT"
[ -d "$CODE_DIR" ] && CHECK_ROOT="$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR" CTH_DATA_DIR="$DATA_DIR"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA_DIR/calculatuhuella.db}"
export APP_ENV="${APP_ENV:-local}"
export SEED_DEMO="true"
source "$CHECK_ROOT/scripts/easy_mac_common.sh"
cth_easy_prepare "$CHECK_ROOT"
clear 2>/dev/null || true
cat <<'BANNER'
============================================================
   CALCULA TU HUELLA V0.45 · PREPARAR Y CERTIFICAR DEMO
============================================================

Este comando completa o repara los datos sintéticos de:
  • Industrias Andinas
  • Greenatics: Yarumal, Támesis y oficina corporativa

No reemplaza datos reales y no debe ejecutarse en producción.
BANNER
if ! cth_easy_python_ready "$CHECK_ROOT"; then
  echo "La aplicación no está instalada. Ejecuta primero el instalador."
  cth_easy_pause
  exit 1
fi
cd "$CHECK_ROOT" || exit 1
"$CHECK_ROOT/.venv/bin/python" -m alembic upgrade head || {
  echo "No fue posible actualizar la base."
  cth_easy_pause
  exit 1
}
if "$CHECK_ROOT/.venv/bin/python" scripts/prepare_demo_environment.py; then
  echo
  echo "Entorno demo preparado y certificado. Ábrelo desde Portafolio → Entorno demo."
  STATUS=0
else
  echo
  echo "La preparación terminó con controles pendientes. Revisa el detalle anterior."
  STATUS=1
fi
cth_easy_pause
exit "$STATUS"
