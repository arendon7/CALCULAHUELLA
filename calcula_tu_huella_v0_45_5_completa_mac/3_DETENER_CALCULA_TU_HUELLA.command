#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
RUNTIME_DIR="${CTH_RUNTIME_DIR:-$INSTALL_ROOT/runtime}"
source "$ROOT/scripts/easy_mac_common.sh"
export CTH_RUNTIME_DIR="$RUNTIME_DIR"
cth_easy_prepare "$ROOT"
clear 2>/dev/null || true
echo "Calcula tu Huella V0.45 · detener aplicación"
echo
PID="$(cat "$RUNTIME_DIR/app.pid" 2>/dev/null || true)"
PORT="$(cat "$RUNTIME_DIR/app.port" 2>/dev/null || true)"
STOPPED=0

if [ -n "$PID" ] && kill -0 "$PID" >/dev/null 2>&1; then
  echo "Deteniendo proceso $PID..."
  kill "$PID" >/dev/null 2>&1 || true
  WAIT=0
  while kill -0 "$PID" >/dev/null 2>&1 && [ "$WAIT" -lt 10 ]; do
    sleep 1
    WAIT=$((WAIT + 1))
  done
  if kill -0 "$PID" >/dev/null 2>&1; then kill -9 "$PID" >/dev/null 2>&1 || true; fi
  STOPPED=1
fi

if [ "$STOPPED" -eq 0 ] && [ -n "$PORT" ] && command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$PIDS" ]; then
    echo "Deteniendo proceso del puerto $PORT..."
    kill $PIDS >/dev/null 2>&1 || true
    STOPPED=1
  fi
fi

rm -f "$RUNTIME_DIR/app.pid" "$RUNTIME_DIR/app.port" "$RUNTIME_DIR/app.url"
if [ "$STOPPED" -eq 1 ]; then echo "Aplicación detenida correctamente."; else echo "La aplicación no estaba ejecutándose."; fi
cth_easy_pause
