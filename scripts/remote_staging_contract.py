from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_BASE_URL = "https://calcula-tu-huella-arendon7-preview.onrender.com"
BASE_URL = os.environ.get("STAGING_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("REMOTE_STAGING_ARTIFACT_DIR", "remote-staging-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_PATH = ARTIFACT_DIR / "remote-staging-evidence.json"


def _assert_safe_target() -> None:
    parsed = urlparse(BASE_URL)
    if parsed.scheme != "https":
        raise AssertionError(f"El staging remoto debe usar HTTPS: {BASE_URL}")
    if not parsed.netloc:
        raise AssertionError(f"STAGING_BASE_URL inválida: {BASE_URL}")


def _timed_get(client: httpx.Client, path: str) -> tuple[httpx.Response, int]:
    started = time.perf_counter()
    response = client.get(path)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return response, elapsed_ms


def _csrf_headers(token: str) -> dict[str, str]:
    return {"x-csrf-token": token}


def main() -> None:
    _assert_safe_target()
    evidence: dict[str, object] = {"base_url": BASE_URL, "contract": "non-mutating-remote-staging-v1"}

    with httpx.Client(base_url=BASE_URL, timeout=20, follow_redirects=False) as client:
        health, health_ms = _timed_get(client, "/api/health")
        if health.status_code != 200:
            raise AssertionError(f"/api/health respondió {health.status_code}: {health.text[:500]}")
        payload = health.json()
        if payload.get("status") != "ok":
            raise AssertionError(f"/api/health no reporta status=ok: {payload!r}")
        if payload.get("environment") != "staging":
            raise AssertionError(f"/api/health no reporta environment=staging: {payload!r}")
        evidence["health"] = {"status": 200, "elapsed_ms": health_ms, "payload": payload}

        for path, marker, key in (
            ("/", "Calcula", "landing"),
            ("/login", "login", "login"),
            ("/diagnostico", "diagn", "diagnostic"),
            ("/legal/privacidad", "priv", "privacy"),
        ):
            response, elapsed_ms = _timed_get(client, path)
            if response.status_code != 200:
                raise AssertionError(f"{path} respondió {response.status_code}")
            if marker.casefold() not in response.text.casefold():
                raise AssertionError(f"{path} no contiene el marcador semántico esperado: {marker!r}")
            evidence[key] = {"status": 200, "elapsed_ms": elapsed_ms}

        home = client.get("/")
        csrf_token = home.cookies.get("cth_csrf") or client.cookies.get("cth_csrf")
        if not csrf_token or len(csrf_token) < 24:
            raise AssertionError("La landing remota no emitió una cookie CSRF válida")
        set_cookie = home.headers.get("set-cookie", "").lower()
        if "secure" not in set_cookie:
            raise AssertionError("La cookie CSRF del staging HTTPS no está marcada Secure")
        evidence["csrf_cookie"] = {"issued": True, "secure": True}

        contact_payload = {
            "company_name": "Remote staging gate",
            "contact_name": "Remote staging gate",
            "email": "remote-gate@example.test",
            "phone": "",
            "sector": "Servicios",
            "interest": "Huella Esencial",
            "message": "Validación no destructiva del contrato remoto.",
            "accept_privacy": "yes",
        }

        rejected_csrf = client.post("/contacto", data=contact_payload)
        if rejected_csrf.status_code != 403:
            raise AssertionError(
                f"/contacto sin header CSRF debía fallar 403, obtuvo {rejected_csrf.status_code}"
            )
        evidence["contact_without_csrf"] = 403

        no_privacy = dict(contact_payload)
        no_privacy.pop("accept_privacy")
        rejected_privacy = client.post(
            "/contacto",
            data=no_privacy,
            headers=_csrf_headers(str(csrf_token)),
        )
        if rejected_privacy.status_code != 400:
            raise AssertionError(
                f"/contacto sin consentimiento debía fallar 400, obtuvo {rejected_privacy.status_code}"
            )
        evidence["contact_without_privacy"] = 400

        invalid_login = client.post(
            "/login",
            data={"email": "remote-gate@example.test", "password": "invalid-remote-gate-password"},
            headers=_csrf_headers(str(csrf_token)),
        )
        if invalid_login.status_code not in {400, 429}:
            raise AssertionError(
                f"Login inválido no fue rechazado de forma controlada: {invalid_login.status_code}"
            )
        evidence["invalid_login"] = invalid_login.status_code

    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
