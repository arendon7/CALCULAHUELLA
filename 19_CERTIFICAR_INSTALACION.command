#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" scripts/platform_preflight.py
"$PYTHON_BIN" scripts/run_test_tier.py smoke
"$PYTHON_BIN" scripts/run_acceptance_certification.py --workers 4 --requests-per-worker 8
printf '\nCertificación local terminada. Revisa release/platform_preflight.json y la carpeta instance/certifications/acceptance.\n'
