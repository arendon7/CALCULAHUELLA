#!/bin/bash
set -u

RUNTIME_DIR="$HOME/Library/Application Support/CalculaTuHuellaDemoFull/runtime"

if [ -f "$RUNTIME_DIR/app.pid" ]; then
  PID="$(cat "$RUNTIME_DIR/app.pid" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" >/dev/null 2>&1 || true
    sleep 1
  fi
fi

rm -f "$RUNTIME_DIR/app.pid" "$RUNTIME_DIR/app.port"
echo "Calcula tu Huella Demo cerrada."
