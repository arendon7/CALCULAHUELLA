from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import argparse
import json

from app.acceptance_certification import run_acceptance_certification


def main() -> int:
    parser = argparse.ArgumentParser(description="Certifica recorridos multiempresa, continuidad y carga local.")
    parser.add_argument("--email", default="admin@calculatuhuella.local")
    parser.add_argument("--password", default="Demo2026!")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--requests-per-worker", type=int, default=8)
    parser.add_argument("--p95-limit-ms", type=float, default=2500.0)
    args = parser.parse_args()
    result = run_acceptance_certification(
        args.email,
        args.password,
        workers=args.workers,
        requests_per_worker=args.requests_per_worker,
        p95_limit_ms=args.p95_limit_ms,
    )
    safe_result = dict(result)
    print(json.dumps(safe_result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
