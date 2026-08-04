#!/usr/bin/env python3
"""Compatibilidad histórica: use import_current_release.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).with_name("import_current_release.py")

if __name__ == "__main__":
    print(
        "DEPRECADO: import_v049_archive.py ya no gobierna la migración. "
        "Se delega al contrato activo migration/current-release.json.",
        file=sys.stderr,
    )
    raise SystemExit(subprocess.call([sys.executable, str(TARGET), *sys.argv[1:]]))
