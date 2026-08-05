#!/usr/bin/env python3
"""Construye una vista estática pública a partir de la aplicación en ejecución.

La vista sirve para revisar landing, identidad, responsive y contenido en cada
commit. No intenta simular autenticación ni operaciones del backend; para eso se
mantiene GitHub Codespaces.
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODESPACES_URL = (
    "https://codespaces.new/arendon7/CALCULAHUELLA"
    "?ref=integration%2Fcanonical&quickstart=1"
)


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def inject_banner(
    html: str,
    *,
    depth: int,
    runtime_version: str,
    target_release: str | None,
    release_status: str | None,
    production_authorized: bool,
) -> str:
    relative = "../" * depth
    runtime_label = html_module.escape(runtime_version)
    target_label = html_module.escape(target_release or "sin definir")
    status_label = html_module.escape(release_status or "sin contrato")
    production_label = "sí" if production_authorized else "no"
    banner = f"""
<div role="status" style="position:sticky;top:0;z-index:99999;padding:10px 16px;background:#0B3B2E;color:#fff;font:600 14px/1.4 Inter,Arial,sans-serif;text-align:center">
  Vista previa estática · runtime {runtime_label} · objetivo {target_label}
  ({status_label}) · producción autorizada: {production_label} ·
  formularios y sesión deshabilitados ·
  <a href="{CODESPACES_URL}" style="color:#fff;text-decoration:underline">abrir aplicación completa en Codespaces</a>
</div>
"""
    if re.search(r"<body[^>]*>", html, flags=re.I):
        html = re.sub(
            r"(<body[^>]*>)",
            r"\1" + banner,
            html,
            count=1,
            flags=re.I,
        )
    else:
        html = banner + html
    html = html.replace(
        'action="/login"', 'action="#" onsubmit="return false"'
    )
    html = html.replace(
        'action="/logout"', 'action="#" onsubmit="return false"'
    )
    html = re.sub(
        r'action="/[^"]*"',
        'action="#" onsubmit="return false"',
        html,
    )
    html = html.replace('href="/static/', f'href="{relative}static/')
    html = html.replace('src="/static/', f'src="{relative}static/')
    html = html.replace("url('/static/", f"url('{relative}static/")
    html = html.replace('href="/login"', f'href="{relative}login/')
    html = html.replace('href="/"', f'href="{relative or "./"}"')
    return html


def runtime_version() -> str:
    sys.path.insert(0, str(ROOT))
    from app.config import settings

    return str(settings.version)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--commit", default=os.getenv("GITHUB_SHA", "local"))
    parser.add_argument(
        "--branch",
        default=os.getenv("GITHUB_REF_NAME", "integration/canonical"),
    )
    args = parser.parse_args()

    release_path = ROOT / "migration" / "current-release.json"
    release = (
        json.loads(release_path.read_text(encoding="utf-8"))
        if release_path.exists()
        else {}
    )
    running_version = runtime_version()
    target_release = release.get("release")
    display_release = release.get("display_release", target_release)
    release_status = release.get("status")
    production_authorized = release.get("production_authorized") is True

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    landing = inject_banner(
        fetch(args.base_url.rstrip("/") + "/"),
        depth=0,
        runtime_version=running_version,
        target_release=display_release,
        release_status=release_status,
        production_authorized=production_authorized,
    )
    login = inject_banner(
        fetch(args.base_url.rstrip("/") + "/login"),
        depth=1,
        runtime_version=running_version,
        target_release=display_release,
        release_status=release_status,
        production_authorized=production_authorized,
    )

    (output / "index.html").write_text(landing, encoding="utf-8")
    (output / "login").mkdir()
    (output / "login" / "index.html").write_text(
        login, encoding="utf-8"
    )

    static_source = ROOT / "app" / "static"
    if not static_source.is_dir():
        raise SystemExit("Falta app/static")
    shutil.copytree(static_source, output / "static")

    status = {
        "project": "Calcula tu Huella",
        "branch": args.branch,
        "commit": args.commit,
        "runtime_version": running_version,
        "target_release": target_release,
        "display_release": display_release,
        "matches_target": running_version == target_release,
        "release_status": release_status,
        "scope_frozen": release.get("scope_frozen", False),
        "production_authorized": production_authorized,
        "external_release_gates": release.get("external_release_gates", []),
        "full_preview": CODESPACES_URL,
    }
    (output / "preview-status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
