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
STARTUP_TIMEOUT_SECONDS = float(os.environ.get("REMOTE_STAGING_STARTUP_TIMEOUT_SECONDS", "120"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REMOTE_STAGING_REQUEST_TIMEOUT_SECONDS", "20"))
POLL_INTERVAL_SECONDS = float(os.environ.get("REMOTE_STAGING_POLL_INTERVAL_SECONDS", "3"))


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


def _wait_for_staging_health(client: httpx.Client) -> tuple[httpx.Response, dict[str, object]]:
    started = time.perf_counter()
    deadline = started + STARTUP_TIMEOUT_SECONDS
    attempts = 0
    last_error = "sin respuesta"

    while True:
        attempts += 1
        request_started = time.perf_counter()
        try:
            response = client.get("/api/health", timeout=REQUEST_TIMEOUT_SECONDS)
            request_ms = round((time.perf_counter() - request_started) * 1000)
            if response.status_code == 200:
                payload = response.json()
                if payload.get("status") == "ok" and payload.get("environment") == "staging":
                    return response, {
                        "status": 200,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000),
                        "last_request_ms": request_ms,
                        "attempts": attempts,
                        "payload": payload,
                    }
                last_error = f"payload inesperado: {payload!r}"
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise AssertionError(
                f"/api/health no quedó sano en {STARTUP_TIMEOUT_SECONDS:.0f}s "
                f"después de {attempts} intento(s). Último resultado: {last_error}"
            )
        time.sleep(min(POLL_INTERVAL_SECONDS, remaining))


def _csrf_headers(token: str) -> dict[str, str]:
    return {"x-csrf-token": token}


def main() -> None:
    _assert_safe_target()
    evidence: dict[str, object] = {"base_url": BASE_URL, "contract": "non-mutating-remote-staging-v2"}

    with httpx.Client(base_url=BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False) as client:
        _, health_evidence = _wait_for_staging_health(client)
        evidence["health"] = health_evidence

        for path, marker, key in (
            ("/", "Calcula", "landing"),
            ("/login", "login", "login"),
            ("/diagnostico", "diagn", "diagnostic"),
            ("/contacto?plan=Huella%20Esencial&sector=Servicios%20y%20oficinas&sites=1&objective=Construir%20la%20primera%20huella", "Solicitar revisión", "contact"),
            ("/legal/privacidad", "priv", "privacy"),
        ):
            response, elapsed_ms = _timed_get(client, path)
            if response.status_code != 200:
                raise AssertionError(f"{path} respondió {response.status_code}")
            if marker.casefold() not in response.text.casefold():
                raise AssertionError(f"{path} no contiene el marcador semántico esperado: {marker!r}")
            evidence[key] = {"status": 200, "elapsed_ms": elapsed_ms}
            if key == "contact":
                body = response.text
                if 'method="post" action="/contacto"' not in body or 'name="_csrf_token"' not in body:
                    raise AssertionError("/contacto no expone el formulario same-origin con CSRF esperado")

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
            "sector": "Servicios y oficinas",
            "interest": "Huella Esencial",
            "message": "Validación no destructiva del contrato remoto.",
            "accept_privacy": "yes",
        }
        rejected_csrf = client.post("/contacto", data=contact_payload)
        if rejected_csrf.status_code != 403:
            raise AssertionError(f"/contacto sin header CSRF debía fallar 403, obtuvo {rejected_csrf.status_code}")
        evidence["contact_without_csrf"] = 403

        no_privacy = dict(contact_payload)
        no_privacy.pop("accept_privacy")
        rejected_privacy = client.post("/contacto", data=no_privacy, headers=_csrf_headers(str(csrf_token)))
        if rejected_privacy.status_code != 400:
            raise AssertionError(f"/contacto sin consentimiento debía fallar 400, obtuvo {rejected_privacy.status_code}")
        evidence["contact_without_privacy"] = 400

        invalid_login = client.post(
            "/login",
            data={"email": "remote-gate@example.test", "password": "invalid-remote-gate-password"},
            headers=_csrf_headers(str(csrf_token)),
        )
        if invalid_login.status_code not in {400, 429}:
            raise AssertionError(f"Login inválido no fue rechazado de forma controlada: {invalid_login.status_code}")
        evidence["invalid_login"] = invalid_login.status_code

    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
