#!/bin/bash
# Selector compartido de Python para macOS.
# Debe cargarse con: source scripts/python_selector.sh

CTH_MIN_PYTHON_MAJOR=3
CTH_MIN_PYTHON_MINOR=11

cth_python_version_ok() {
  local candidate="$1"
  "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

cth_python_version() {
  local candidate="$1"
  "$candidate" -c 'import platform; print(platform.python_version())' 2>/dev/null || true
}

cth_find_python() {
  local candidates=()
  local candidate resolved

  if [ -n "${PYTHON_BIN:-}" ]; then
    candidates+=("$PYTHON_BIN")
  fi

  # Preferimos versiones explícitas para no tomar el Python 3.9 de macOS o Conda base.
  candidates+=(
    "python3.13"
    "python3.12"
    "python3.11"
    "/opt/homebrew/bin/python3.13"
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "/usr/local/bin/python3.13"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3.11"
    "python3"
    "python"
  )

  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == */* ]]; then
      [ -x "$candidate" ] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [ -n "$resolved" ] || continue
    fi

    if cth_python_version_ok "$resolved"; then
      CTH_PYTHON_BIN="$resolved"
      CTH_PYTHON_VERSION="$(cth_python_version "$resolved")"
      export CTH_PYTHON_BIN CTH_PYTHON_VERSION
      return 0
    fi
  done

  return 1
}

cth_print_python_diagnostics() {
  echo "Diagnóstico de Python:"
  local candidate resolved version
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    resolved="$(command -v "$candidate" 2>/dev/null || true)"
    if [ -n "$resolved" ]; then
      version="$(cth_python_version "$resolved")"
      echo "  - $candidate: $resolved (Python ${version:-desconocido})"
    fi
  done
}
