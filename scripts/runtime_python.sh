#!/usr/bin/env bash

cth_runtime_python() {
  local root="${1:-$PWD}"
  local configured="${CTH_PYTHON_BIN:-}"
  local candidate=""

  if [ -n "$configured" ] && [ -x "$configured" ]; then
    CTH_RUNTIME_PYTHON="$configured"
    export CTH_RUNTIME_PYTHON
    return 0
  fi

  candidate="$root/.venv/bin/python"
  if [ -x "$candidate" ]; then
    CTH_RUNTIME_PYTHON="$candidate"
    export CTH_RUNTIME_PYTHON
    return 0
  fi

  # Los instaladores locales usan la .venv del proyecto. En Docker, las
  # dependencias se instalan en el Python del contenedor y no existe .venv.
  if [ -f "/.dockerenv" ] || [ "${CTH_ALLOW_SYSTEM_PYTHON:-false}" = "true" ]; then
    candidate="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      CTH_RUNTIME_PYTHON="$candidate"
      export CTH_RUNTIME_PYTHON
      return 0
    fi
  fi

  echo "No existe un Python ejecutable para Calcula tu Huella." >&2
  echo "Instalación local: ejecuta primero ./install_mac.sh" >&2
  echo "Docker: verifica que la imagen incluya python3 o define CTH_PYTHON_BIN." >&2
  return 1
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
