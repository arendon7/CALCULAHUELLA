#!/bin/bash
set -euo pipefail

INSTALL_ROOT="$HOME/Library/Application Support/CalculaTuHuellaDemoFull"
CODE_DIR="$INSTALL_ROOT/current"
DATA_DIR="$INSTALL_ROOT/data"
RUNTIME_DIR="$INSTALL_ROOT/runtime"
PY="$RUNTIME_DIR/python/bin/python3"

test -x "$PY" || { echo "Primero ejecuta 1_INSTALAR_Y_ABRIR_DEMO.command"; read -r; exit 1; }
mkdir -p "$DATA_DIR/logs" "$RUNTIME_DIR"

export PYTHONPATH="$RUNTIME_DIR/vendor:$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR"
export DATABASE_URL="sqlite:///$DATA_DIR/calculatuhuella.db"
export APP_ENV=local
export SEED_DEMO=true
export SCHEDULER_ENABLED=0
export STRUCTURED_LOGGING=0
export HOST=127.0.0.1
export OPEN_BROWSER=0
export TRUSTED_HOSTS="localhost,127.0.0.1,testserver"

cd "$CODE_DIR"
PORT=""
for P in $(seq 8765 8775); do
  if ! /usr/sbin/lsof -nP -iTCP:"$P" -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="$P"
    break
  fi
done
test -n "$PORT" || { echo "No hay puerto libre entre 8765 y 8775."; read -r; exit 1; }

export PORT
export PUBLIC_BASE_URL="http://127.0.0.1:$PORT"

if [ -f "$RUNTIME_DIR/app.pid" ]; then
  OLD_PID="$(cat "$RUNTIME_DIR/app.pid" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    OLD_PORT="$(cat "$RUNTIME_DIR/app.port" 2>/dev/null || echo 8765)"
    if /usr/bin/curl -fsS --max-time 2 "http://127.0.0.1:$OLD_PORT/api/health" >/dev/null 2>&1; then
      /usr/bin/open "http://127.0.0.1:$OLD_PORT/login"
      exit 0
    fi
  fi
fi

"$PY" -m alembic upgrade head >>"$DATA_DIR/logs/demo.log" 2>&1
nohup "$PY" run.py >>"$DATA_DIR/logs/demo.log" 2>&1 </dev/null &
PID=$!
echo "$PID" > "$RUNTIME_DIR/app.pid"
echo "$PORT" > "$RUNTIME_DIR/app.port"

READY=0
for _ in $(seq 1 90); do
  if /usr/bin/curl -fsS --max-time 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  kill -0 "$PID" >/dev/null 2>&1 || break
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "La demo no inició. Últimas líneas del log:"
  tail -n 60 "$DATA_DIR/logs/demo.log" || true
  read -r
  exit 1
fi

echo "Demo lista: http://127.0.0.1:$PORT/login"
echo "Consultor: consultor@calculatuhuella.local / Demo2026!"
/usr/bin/open "http://127.0.0.1:$PORT/login"
