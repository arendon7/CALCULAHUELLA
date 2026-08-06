from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'instance'}
FORBIDDEN_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.pyc', '.pyo', '.zip'}
SECRET_PATTERNS = [re.compile(r'BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY'), re.compile(r'AKIA[0-9A-Z]{16}')]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-manifest', action='store_true')
    args = parser.parse_args()
    errors: list[str] = []
    if (ROOT / 'VERSION').read_text(encoding='utf-8').strip() != '1.0.0':
        errors.append('VERSION no es 1.0.0')
    config = (ROOT / 'app/config.py').read_text(encoding='utf-8')
    if 'version: str = "1.0.0"' not in config:
        errors.append('app/config.py no declara 1.0.0')
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            errors.append(f'Elemento prohibido: {rel}')
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f'Archivo generado/prohibido: {rel}')
        if path.is_file() and path.stat().st_size <= 2_000_000 and path.suffix.lower() in {'.py','.yml','.yaml','.json','.md','.txt','.env','.example','.sh','.ps1','.bat','.command'}:
            try:
                text = path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f'Posible secreto en {rel}')
    if not args.skip_manifest:
        manifest = ROOT / 'MANIFIESTO_SHA256_CANONICO.txt'
        if not manifest.exists():
            errors.append('Falta MANIFIESTO_SHA256_CANONICO.txt')
        else:
            for line in manifest.read_text(encoding='utf-8').splitlines():
                if not line.strip():
                    continue
                expected, rel = line.split('  ', 1)
                path = ROOT / rel
                if not path.exists() or sha256(path) != expected:
                    errors.append(f'Hash inválido: {rel}')
    if errors:
        print('\n'.join(f'ERROR: {e}' for e in errors))
        return 1
    print('Versión canónica verificada correctamente.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
