#!/bin/bash
set -u
cd "$(dirname "$0")"
source scripts/python_selector.sh

echo "Calcula tu Huella · diagnóstico macOS"
echo "Directorio: $PWD"
echo "macOS: $(sw_vers -productVersion 2>/dev/null || echo desconocido)"
echo "Arquitectura: $(uname -m)"
echo "Shell: ${SHELL:-desconocido}"
echo "Conda activo: ${CONDA_DEFAULT_ENV:-no}"
echo
cth_print_python_diagnostics

echo
if cth_find_python; then
  echo "Python compatible encontrado: $CTH_PYTHON_BIN ($CTH_PYTHON_VERSION)"
else
  echo "No se encontró Python 3.11 o superior en PATH."
fi

if [ -x .venv/bin/python ]; then
  echo "Entorno .venv: $(.venv/bin/python --version 2>&1)"
  if cth_python_version_ok .venv/bin/python; then
    echo "Estado .venv: compatible"
  else
    echo "Estado .venv: incompatible; ejecuta ./repair_mac.sh"
  fi
else
  echo "Entorno .venv: no creado"
fi

if command -v lsof >/dev/null 2>&1 && lsof -i :8765 >/dev/null 2>&1; then
  echo "Puerto 8765: ocupado"
else
  echo "Puerto 8765: disponible"
fi
