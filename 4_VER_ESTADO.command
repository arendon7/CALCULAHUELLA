#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
CODE_DIR="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"
DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
RUNTIME_DIR="${CTH_RUNTIME_DIR:-$INSTALL_ROOT/runtime}"
CHECK_ROOT="$ROOT"
[ -d "$CODE_DIR" ] && CHECK_ROOT="$CODE_DIR"
export CTH_DATA_DIR="$DATA_DIR" CTH_RUNTIME_DIR="$RUNTIME_DIR"
source "$CHECK_ROOT/scripts/easy_mac_common.sh"
cth_easy_prepare "$CHECK_ROOT"
clear 2>/dev/null || true
echo "Calcula tu Huella V1.0.0 · estado"
echo "Código: $CHECK_ROOT"
echo "Datos: $DATA_DIR"
echo
if cth_easy_python_ready "$CHECK_ROOT"; then
  echo "Instalación: correcta"
  echo "Python: $($CHECK_ROOT/.venv/bin/python --version 2>&1)"
else
  echo "Instalación: pendiente o incompleta"
fi
if [ -f "$DATA_DIR/calculatuhuella.db" ]; then echo "Base de datos: disponible"; else echo "Base de datos: pendiente"; fi
PID="$(cth_easy_running_pid "$CHECK_ROOT" 2>/dev/null || true)"
PORT="$(cat "$RUNTIME_DIR/app.port" 2>/dev/null || true)"
if [ -n "$PID" ] && [ -n "$PORT" ]; then
  URL="http://127.0.0.1:${PORT}/api/health"
  if curl -fsS --max-time 2 "$URL" >/dev/null 2>&1; then
    echo "Aplicación: ejecutándose"
    echo "Proceso: $PID"
    echo "Dirección: http://127.0.0.1:${PORT}/login"
  else
    echo "Aplicación: proceso detectado, pero no responde"
  fi
else
  echo "Aplicación: detenida"
fi
echo "Registro: $DATA_DIR/logs/aplicacion_mac.log"
cth_easy_pause
