#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
INSTALLED_CODE="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"

# Si se abrió desde el paquete descargado y ya está instalada, usa la instalación estable.
if [ "$ROOT" != "$INSTALLED_CODE" ] && [ -f "$INSTALLED_CODE/ABRIR_CALCULA_TU_HUELLA.command" ]; then
  exec /bin/bash "$INSTALLED_CODE/ABRIR_CALCULA_TU_HUELLA.command" "$@"
fi

# Si aún no está instalada, este mismo acceso inicia el instalador completo.
if [ ! -x "$ROOT/.venv/bin/python" ] && [ -f "$ROOT/INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command" ] && [ "$ROOT" != "$INSTALLED_CODE" ]; then
  exec /bin/bash "$ROOT/INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command"
fi

DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
RUNTIME_DIR="${CTH_RUNTIME_DIR:-$INSTALL_ROOT/runtime}"
DB_PATH="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
export CTH_DATA_DIR="$DATA_DIR" CTH_RUNTIME_DIR="$RUNTIME_DIR" CTH_DB_PATH="$DB_PATH"
export INSTANCE_DIR="$DATA_DIR"
export DATABASE_URL="sqlite:///$DB_PATH"

cd "$ROOT" || exit 1
source "$ROOT/scripts/easy_mac_common.sh"
source "$ROOT/scripts/runtime_python.sh"
cth_easy_prepare "$ROOT"
PAUSE=1
[ "${1:-}" = "--sin-pausa" ] && PAUSE=0

clear 2>/dev/null || true
cat <<'BANNER'
============================================================
              CALCULA TU HUELLA V0.45.5 · IMPORTACIÓN GUIADA
============================================================
BANNER

if ! cth_easy_python_ready "$ROOT"; then
  echo "La instalación está incompleta. Reparando automáticamente..."
  "$ROOT/install_mac.sh" || {
    echo "No fue posible completar la reparación."
    [ "$PAUSE" -eq 1 ] && cth_easy_pause
    exit 1
  }
fi

RUNNING_PID="$(cth_easy_running_pid "$ROOT" 2>/dev/null || true)"
if [ -n "$RUNNING_PID" ]; then
  PORT="$(cat "$RUNTIME_DIR/app.port" 2>/dev/null || echo 8765)"
  URL="http://127.0.0.1:${PORT}/login"
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "La aplicación ya está ejecutándose."
    echo "Dirección: $URL"
    cth_easy_open_url "$URL"
    [ "$PAUSE" -eq 1 ] && cth_easy_pause
    exit 0
  fi
fi

rm -f "$RUNTIME_DIR/app.pid" "$RUNTIME_DIR/app.port" "$RUNTIME_DIR/app.url"
cth_runtime_python "$ROOT" || {
  [ "$PAUSE" -eq 1 ] && cth_easy_pause
  exit 1
}
PY="$CTH_RUNTIME_PYTHON"
REQUESTED_PORT="${PORT:-8765}"
PORT="$(cth_choose_port "$REQUESTED_PORT")" || {
  [ "$PAUSE" -eq 1 ] && cth_easy_pause
  exit 1
}
URL="http://127.0.0.1:${PORT}/login"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
LOG="$DATA_DIR/logs/aplicacion_mac.log"

export APP_ENV=local
export SEED_DEMO=true
export HOST=127.0.0.1
export PORT
export OPEN_BROWSER=0
export TRUSTED_HOSTS="localhost,127.0.0.1,testserver"
export PUBLIC_BASE_URL="http://127.0.0.1:${PORT}"

mkdir -p "$DATA_DIR/logs" "$RUNTIME_DIR"
echo "Preparando base de datos..."
"$PY" -m alembic upgrade head >>"$LOG" 2>&1 || {
  echo "No fue posible actualizar la base de datos."
  tail -n 30 "$LOG" 2>/dev/null || true
  [ "$PAUSE" -eq 1 ] && cth_easy_pause
  exit 1
}

echo "Iniciando en el puerto $PORT..."
nohup "$PY" run.py >>"$LOG" 2>&1 </dev/null &
PID=$!
printf '%s\n' "$PID" > "$RUNTIME_DIR/app.pid"
printf '%s\n' "$PORT" > "$RUNTIME_DIR/app.port"
printf '%s\n' "$URL" > "$RUNTIME_DIR/app.url"

READY=0
COUNT=0
while [ "$COUNT" -lt 90 ]; do
  if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    READY=1
    break
  fi
  if ! kill -0 "$PID" >/dev/null 2>&1; then
    break
  fi
  COUNT=$((COUNT + 1))
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo
  echo "La aplicación no alcanzó el estado listo."
  echo "Últimas líneas del registro:"
  tail -n 40 "$LOG" 2>/dev/null || true
  rm -f "$RUNTIME_DIR/app.pid" "$RUNTIME_DIR/app.port" "$RUNTIME_DIR/app.url"
  [ "$PAUSE" -eq 1 ] && cth_easy_pause
  exit 1
fi

echo
echo "Aplicación iniciada correctamente."
echo "Dirección: $URL"
echo "Usuario de demostración: consultor@calculatuhuella.local"
echo "Contraseña: Demo2026!"
echo "Datos persistentes: $DATA_DIR"
cth_easy_open_url "$URL"
[ "$PAUSE" -eq 1 ] && cth_easy_pause
exit 0
