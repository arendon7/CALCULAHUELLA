from __future__ import annotations

import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.public_contact_contract import (
    PUBLIC_CONTACT_LEAD_SOURCE,
    PUBLIC_CONTACT_LEAD_STATUS,
    PUBLIC_CONTACT_SUCCESS_LOCATION,
)

ARTIFACT_DIR = Path(os.environ.get("SERVERLESS_STAGING_ARTIFACT_DIR", "serverless-staging-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "http://127.0.0.1:8791"


def _lead_snapshot(db_path: Path) -> dict[str, object]:
    if not db_path.exists():
        raise AssertionError(f"La base efímera no existe: {db_path}")
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("select count(*) from commercial_leads").fetchone()[0]
        latest = conn.execute(
            "select company_name, contact_name, email, status, source from commercial_leads order by id desc limit 1"
        ).fetchone()
    return {
        "count": int(count),
        "latest": list(latest) if latest else None,
    }


def _wait_until_ready(client: httpx.Client, process: subprocess.Popen[str], log_path: Path) -> dict[str, object]:
    deadline = time.monotonic() + 45
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            raise AssertionError(f"Uvicorn terminó antes de estar listo ({process.returncode}).\n{log[-6000:]}")
        try:
            response = client.get("/api/health")
            if response.status_code == 200:
                payload = response.json()
                if payload.get("status") == "ok":
                    return payload
                last_error = f"payload inesperado: {payload!r}"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = repr(exc)
        time.sleep(0.25)
    raise AssertionError(f"El staging no respondió /api/health: {last_error}")


def _csrf_headers(token: str) -> dict[str, str]:
    return {
        "x-csrf-token": token,
        "cookie": f"cth_csrf={token}",
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cth-vercel-staging-") as temp_dir:
        instance_dir = Path(temp_dir)
        db_path = instance_dir / "calculatuhuella.db"
        log_path = ARTIFACT_DIR / "uvicorn.log"
        evidence_path = ARTIFACT_DIR / "serverless-staging-evidence.json"

        env = os.environ.copy()
        env.update(
            {
                "APP_ENV": "staging",
                "INSTANCE_DIR": str(instance_dir),
                "DATABASE_URL": f"sqlite:///{db_path}",
                "SESSION_SECRET": secrets.token_urlsafe(48),
                "SESSION_HTTPS_ONLY": "true",
                "TRUSTED_HOSTS": "127.0.0.1,localhost",
                "SEED_DEMO": "false",
                "STORAGE_BACKEND": "local",
                "EMAIL_BACKEND": "disabled",
                "SCHEDULER_ENABLED": "false",
                "DEPLOYMENT_STRICT": "false",
                "OPEN_BROWSER": "0",
                "WEB_CONCURRENCY": "1",
                "STRUCTURED_LOGGING": "false",
                "PBKDF2_ITERATIONS": "10000",
            }
        )

        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "api.index:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8791",
                    "--no-access-log",
                ],
                cwd=ROOT,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

            evidence: dict[str, object] = {}
            try:
                with httpx.Client(base_url=BASE_URL, timeout=10, follow_redirects=False) as client:
                    health = _wait_until_ready(client, process, log_path)
                    if health.get("environment") != "staging":
                        raise AssertionError(f"/api/health no reporta staging: {health!r}")
                    evidence["health"] = health

                    login = client.get("/login")
                    if login.status_code != 200 or "login" not in login.text.lower():
                        raise AssertionError(f"/login inválido: {login.status_code}")
                    evidence["login_get"] = login.status_code

                    diagnostic = client.get("/diagnostico")
                    if diagnostic.status_code != 200 or "diagn" not in diagnostic.text.lower():
                        raise AssertionError(f"/diagnostico inválido: {diagnostic.status_code}")
                    evidence["diagnostic_get"] = diagnostic.status_code

                    privacy = client.get("/legal/privacidad")
                    if privacy.status_code != 200:
                        raise AssertionError(f"/legal/privacidad inválido: {privacy.status_code}")
                    evidence["privacy_get"] = privacy.status_code

                    home = client.get("/")
                    if home.status_code != 200:
                        raise AssertionError(f"Landing FastAPI inválida: {home.status_code}")
                    csrf_token = home.cookies.get("cth_csrf")
                    if not csrf_token or len(csrf_token) < 24:
                        raise AssertionError("La respuesta pública no emitió cookie CSRF válida")
                    evidence["csrf_cookie"] = "issued"

                    lead_before = _lead_snapshot(db_path)

                    contact_payload = {
                        "company_name": "Empresa Gate Staging",
                        "contact_name": "Persona Gate",
                        "email": "gate@example.test",
                        "phone": "",
                        "sector": "Servicios",
                        "interest": "Huella Esencial",
                        "message": "Solicitud automatizada de certificación del staging serverless.",
                        "accept_privacy": "yes",
                    }

                    rejected_csrf = client.post("/contacto", data=contact_payload)
                    if rejected_csrf.status_code != 403:
                        raise AssertionError(f"/contacto sin CSRF debía fallar 403, obtuvo {rejected_csrf.status_code}")
                    if _lead_snapshot(db_path)["count"] != lead_before["count"]:
                        raise AssertionError("Un POST sin CSRF creó un lead")
                    evidence["contact_without_csrf"] = 403

                    no_privacy = dict(contact_payload)
                    no_privacy.pop("accept_privacy")
                    rejected_privacy = client.post(
                        "/contacto",
                        data=no_privacy,
                        headers=_csrf_headers(csrf_token),
                    )
                    if rejected_privacy.status_code != 400:
                        raise AssertionError(
                            f"/contacto sin privacidad debía fallar 400, obtuvo {rejected_privacy.status_code}"
                        )
                    if _lead_snapshot(db_path)["count"] != lead_before["count"]:
                        raise AssertionError("Un POST sin consentimiento creó un lead")
                    evidence["contact_without_privacy"] = 400

                    accepted = client.post(
                        "/contacto",
                        data=contact_payload,
                        headers=_csrf_headers(csrf_token),
                    )
                    if accepted.status_code != 303:
                        raise AssertionError(f"/contacto válido debía responder 303, obtuvo {accepted.status_code}")
                    accepted_location = accepted.headers.get("location", "")
                    if accepted_location != PUBLIC_CONTACT_SUCCESS_LOCATION:
                        raise AssertionError(f"Redirect comercial inesperado: {accepted_location!r}")
                    lead_after = _lead_snapshot(db_path)
                    if lead_after["count"] != int(lead_before["count"]) + 1:
                        raise AssertionError(f"El lead válido no se persistió exactamente una vez: {lead_after!r}")
                    latest = lead_after["latest"] or []
                    if latest[:3] != ["Empresa Gate Staging", "Persona Gate", "gate@example.test"]:
                        raise AssertionError(f"Lead persistido inesperado: {latest!r}")
                    if latest[3:] != [PUBLIC_CONTACT_LEAD_STATUS, PUBLIC_CONTACT_LEAD_SOURCE]:
                        raise AssertionError(f"Estado/origen comercial inesperados: {latest!r}")
                    evidence["contact_valid"] = {
                        "status": 303,
                        "lead_delta": 1,
                        "location": accepted_location,
                        "lead_status": latest[3],
                        "lead_source": latest[4],
                    }

                    invalid_login = client.post(
                        "/login",
                        data={"email": "nobody@example.test", "password": "incorrecta"},
                        headers=_csrf_headers(csrf_token),
                    )
                    if invalid_login.status_code not in {400, 429}:
                        raise AssertionError(f"Login inválido no fue rechazado de forma controlada: {invalid_login.status_code}")
                    evidence["login_invalid"] = invalid_login.status_code

                    evidence["runtime_contract"] = {
                        "instance_dir": "ephemeral",
                        "database": "isolated-sqlite",
                        "scheduler": False,
                        "email": "disabled",
                        "deployment_strict": False,
                    }
            finally:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
                    process.kill()
                    process.wait(timeout=5)

        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
