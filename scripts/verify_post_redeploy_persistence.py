from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

BASE_URL = os.environ.get("STAGING_BASE_URL", "https://calcula-tu-huella-arendon7-preview.onrender.com").rstrip("/")
PASSWORD = os.environ.get("STAGING_DEMO_PASSWORD", "Demo2026!")
ARTIFACT_DIR = Path(os.environ.get("POST_REDEPLOY_ARTIFACT_DIR", "post-redeploy-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_PATH = ARTIFACT_DIR / "post-redeploy-persistence.json"
TICKET_PATH = "/soporte/13"
SUBJECT = "UAT online persistencia 1786604659"
RESPONSE = "Respuesta UAT del consultor: caso recibido y trazabilidad entre actores confirmada."
RESOLUTION = "UAT online completada: persistencia entre sesiones y relevo cliente-consultor verificados."


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=25, follow_redirects=False) as client:
        login_page = client.get("/login")
        if login_page.status_code != 200:
            raise AssertionError(f"Login page respondió {login_page.status_code}")
        csrf = client.cookies.get("cth_csrf")
        if not csrf:
            raise AssertionError("No se emitió CSRF para la sesión post-redeploy")
        logged = client.post(
            "/login",
            data={"email": "consultor@calculatuhuella.local", "password": PASSWORD},
            headers={"x-csrf-token": str(csrf)},
        )
        if logged.status_code != 303:
            raise AssertionError(f"Login post-redeploy falló: {logged.status_code}")
        page = client.get(TICKET_PATH)
        if page.status_code != 200:
            raise AssertionError(f"{TICKET_PATH} respondió {page.status_code} después del redeploy")
        body = page.text
        missing = [value for value in (SUBJECT, RESPONSE, RESOLUTION) if value not in body]
        if missing:
            raise AssertionError(f"El caso UAT perdió contenido después del redeploy: {missing}")
        if "Cerrado" not in body:
            raise AssertionError("El estado Cerrado del caso UAT no sobrevivió al redeploy")

    evidence = {
        "base_url": BASE_URL,
        "contract": "post-redeploy-persistence-v1",
        "ticket_path": TICKET_PATH,
        "subject_preserved": True,
        "consultor_response_preserved": True,
        "resolution_preserved": True,
        "closed_status_preserved": True,
        "fresh_authenticated_session": True,
        "result": "PASS",
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
