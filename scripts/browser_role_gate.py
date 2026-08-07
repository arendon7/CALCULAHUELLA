from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

BASE_URL = os.environ.get("ROLE_GATE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("ROLE_GATE_ARTIFACT_DIR", "role-gate-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
PASSWORD = "Demo2026!"

ROLE_CASES: dict[str, dict[str, object]] = {
    "Administrador": {
        "email": "admin@calculatuhuella.local",
        "navigation": [
            "Mi trabajo", "Portafolio de empresas", "Continuar recorrido", "Datos y avance",
            "Calidad y riesgos", "Resultados", "Cierre e informes", "Plan de reducción",
        ],
        "can_create": True,
        "scope": "all",
    },
    "Consultor": {
        "email": "consultor@calculatuhuella.local",
        "navigation": [
            "Mi trabajo", "Continuar recorrido", "Fuentes y límites", "Datos y evidencias",
            "Calidad y revisión", "Resultados", "Cierre e informes", "Plan de reducción",
        ],
        "can_create": True,
        "scope": "all",
    },
    "Cliente": {
        "email": "cliente@calculatuhuella.local",
        "navigation": [
            "Mi trabajo", "Continuar mi recorrido", "Cargar datos", "Datos y soportes",
            "Revisar calidad", "Ver resultados",
        ],
        "can_create": False,
        "scope": "mine",
    },
    "Revisor": {
        "email": "revisor@calculatuhuella.local",
        "navigation": [
            "Mi trabajo", "Prioridades de revisión", "Calidad de datos", "Revisión técnica",
            "Resultados calculados", "Cierre metodológico", "Expediente de cierre",
        ],
        "can_create": False,
        "scope": "all",
    },
    "Verificador": {
        "email": "verificador@calculatuhuella.local",
        "navigation": [
            "Mi trabajo", "Plan de verificación", "Paquete verificable", "Metodología y límites",
            "Reproducir resultados", "Hallazgos", "Aseguramiento",
        ],
        "can_create": False,
        "scope": "all",
    },
}

SENSITIVE_ROUTES = {
    "/usuarios": {"Administrador"},
    "/operacion": {"Administrador"},
    "/portafolio": {"Administrador", "Consultor", "Revisor", "Verificador"},
    "/metodologia/nucleo": {"Administrador", "Consultor", "Revisor", "Verificador"},
    "/aseguramiento": {"Administrador", "Consultor", "Revisor", "Verificador"},
}


def _login(page: Page, email: str) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(PASSWORD)
    page.locator("form.login-form button").click()
    page.wait_for_load_state("networkidle")
    if "/login" in page.url:
        raise AssertionError(f"El login demo no salió de /login para {email}.")


def _json_response(response) -> dict[str, object]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError(f"Respuesta JSON inesperada: {payload!r}")
    return payload


def _route_contract(context: BrowserContext, role: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for route, allowed_roles in SENSITIVE_ROUTES.items():
        response = context.request.get(f"{BASE_URL}{route}", fail_on_status_code=False)
        expected = 200 if role in allowed_roles else 403
        if response.status != expected:
            raise AssertionError(
                f"{role}: {route} devolvió {response.status}; se esperaba {expected}."
            )
        results.append({"route": route, "status": response.status, "expected": expected})
    return results


def _role_contract(browser, role: str, spec: dict[str, object]) -> dict[str, object]:
    console_errors: list[str] = []
    page_errors: list[str] = []
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    _login(page, str(spec["email"]))
    page.evaluate("window.localStorage.setItem('cth-tour-v14-' + document.body.dataset.role.toLowerCase().replaceAll(' ', '-'), 'completed')")

    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    response = page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    if response is None or response.status != 200:
        raise AssertionError(f"{role}: /mi-trabajo no devolvió 200.")

    rendered_role = page.locator("body").get_attribute("data-role")
    if rendered_role != role:
        raise AssertionError(f"Perfil activo incorrecto: esperado {role}, recibido {rendered_role}.")

    labels = [text.strip() for text in page.locator(".nav-item").all_inner_texts() if text.strip()]
    expected_labels = list(spec["navigation"])
    if labels != expected_labels:
        raise AssertionError(f"{role}: navegación esencial inesperada. actual={labels}; esperada={expected_labels}")
    if "Centro de trabajo" in labels or labels[0] != "Mi trabajo":
        raise AssertionError(f"{role}: la navegación esencial no prioriza Mi trabajo correctamente.")

    create_form_count = page.locator(".work-create-form").count()
    expected_create = bool(spec["can_create"])
    if bool(create_form_count) is not expected_create:
        raise AssertionError(f"{role}: visibilidad de creación de tareas incorrecta.")

    scope_count = page.locator('select[name="scope"]').count()
    expected_scope = str(spec["scope"])
    if (scope_count > 0) is (expected_scope == "mine"):
        raise AssertionError(f"{role}: visibilidad del selector de alcance incorrecta.")

    api = context.request.get(f"{BASE_URL}/api/mi-trabajo?scope=all", fail_on_status_code=False)
    if api.status != 200:
        raise AssertionError(f"{role}: API Mi trabajo devolvió {api.status}.")
    payload = _json_response(api)
    if payload.get("scope") != expected_scope:
        raise AssertionError(f"{role}: scope API={payload.get('scope')}; esperado={expected_scope}.")

    route_results = _route_contract(context, role)

    screenshot_name = f"mi-trabajo-{role.lower()}.png"
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    page.evaluate("document.querySelectorAll('dialog[open]').forEach(d => { try { d.close(); } catch (_) { d.removeAttribute('open'); } })")
    page.screenshot(path=str(ARTIFACT_DIR / screenshot_name), full_page=True)

    if console_errors or page_errors:
        raise AssertionError(f"{role}: errores de navegador. console={console_errors}; page={page_errors}")

    result = {
        "role": role,
        "email": spec["email"],
        "navigation": labels,
        "can_create": expected_create,
        "scope": payload.get("scope"),
        "visible_items": len(payload.get("items") or []),
        "sensitive_routes": route_results,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "screenshot": screenshot_name,
    }
    context.close()
    return result


def main() -> int:
    evidence: dict[str, object] = {
        "engine": "chromium",
        "base_url": BASE_URL,
        "roles": [],
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for role, spec in ROLE_CASES.items():
            evidence["roles"].append(_role_contract(browser, role, spec))
        browser.close()

    path = ARTIFACT_DIR / "role-gate.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
