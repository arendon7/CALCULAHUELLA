#!/usr/bin/env bash

cth_runtime_python() {
  local root="${1:-$PWD}"
  local candidate="${CTH_PYTHON_BIN:-$root/.venv/bin/python}"
  if [ ! -x "$candidate" ]; then
    echo "No existe un Python local ejecutable en: $candidate" >&2
    echo "Ejecuta primero: ./install_mac.sh" >&2
    return 1
  fi
  CTH_RUNTIME_PYTHON="$candidate"
  export CTH_RUNTIME_PYTHON
}

cth_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

cth_choose_port() {
  local requested="${1:-8765}"
  local port="$requested"
  if ! cth_port_in_use "$port"; then
    printf '%s\n' "$port"
    return 0
  fi
  for port in $(seq $((requested + 1)) $((requested + 10))); do
    if ! cth_port_in_use "$port"; then
      printf '%s\n' "$port"
      return 0
    fi
  done
  echo "No se encontró un puerto libre entre $requested y $((requested + 10))." >&2
  return 1
}
