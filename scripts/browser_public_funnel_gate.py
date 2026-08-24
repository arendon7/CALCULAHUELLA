from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from sqlalchemy import select

from app.database import CommercialLead, DiagnosticAssessment, SessionLocal


BASE_URL = os.environ.get("PUBLIC_FUNNEL_GATE_BASE_URL", "http://127.0.0.1:8769").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("PUBLIC_FUNNEL_GATE_ARTIFACT_DIR", "public-funnel-gate-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
EMAIL = "public-funnel-v2603@prospecto.test"


def _assert_step(page: Page, number: int) -> None:
    step = page.locator(f'[data-diagnosis-step="{number}"]')
    step.wait_for(state="visible")
    if step.get_attribute("aria-hidden") == "true":
        raise AssertionError(f"Paso {number} quedó marcado aria-hidden durante el recorrido público.")


def _assert_no_horizontal_overflow(page: Page, label: str) -> dict[str, int]:
    metrics = page.evaluate(
        """() => ({
            viewport: document.documentElement.clientWidth,
            scroll: document.documentElement.scrollWidth
        })"""
    )
    if metrics["scroll"] > metrics["viewport"] + 1:
        raise AssertionError(
            f"{label} presenta overflow horizontal: viewport={metrics['viewport']}, scroll={metrics['scroll']}"
        )
    return metrics


def _canonical_footer_logo_state(page: Page) -> dict[str, object]:
    footer_logo = page.locator("footer .canonical-footer-logo")
    footer_logo.wait_for(state="visible")
    state = footer_logo.evaluate(
        """img => ({
            naturalWidth: img.naturalWidth,
            naturalHeight: img.naturalHeight,
            filter: getComputedStyle(img).filter,
            objectFit: getComputedStyle(img).objectFit
        })"""
    )
    if state["naturalWidth"] <= 0 or state["naturalHeight"] <= 0:
        raise AssertionError(f"El logo canónico del footer no cargó: {state!r}")
    if state["filter"] != "none":
        raise AssertionError(
            "El logo canónico del footer está siendo reinterpretado por CSS: "
            f"filter={state['filter']!r}"
        )
    return state


def _persistence_contract() -> dict[str, object]:
    with SessionLocal() as session:
        lead = session.scalar(
            select(CommercialLead)
            .where(CommercialLead.email == EMAIL)
            .order_by(CommercialLead.id.desc())
            .limit(1)
        )
        if lead is None:
            raise AssertionError("El funnel público terminó sin persistir el lead autorizado.")
        assessment = session.scalar(
            select(DiagnosticAssessment)
            .where(DiagnosticAssessment.lead_id == lead.id)
            .order_by(DiagnosticAssessment.id.desc())
            .limit(1)
        )
        if assessment is None:
            raise AssertionError("El funnel público terminó sin vincular el diagnóstico al lead.")
        if "Autorización de privacidad: sí" not in lead.notes:
            raise AssertionError("El lead público no conserva evidencia de autorización de privacidad.")
        if assessment.recommended_package_code != lead.recommended_plan_code:
            raise AssertionError(
                "La recomendación persistida en diagnóstico y lead no coincide: "
                f"assessment={assessment.recommended_package_code}, lead={lead.recommended_plan_code}"
            )
        return {
            "lead_id": lead.id,
            "assessment_id": assessment.id,
            "assessment_code": assessment.assessment_code,
            "package": assessment.recommended_package_code,
            "complexity": assessment.complexity_level,
            "maturity": assessment.maturity_level,
            "privacy_authorized": True,
        }


def main() -> int:
    evidence: dict[str, object] = {
        "engine": "chromium",
        "base_url": BASE_URL,
        "journey": "landing -> prefill -> diagnosis -> consent -> result -> mobile result",
        "email": EMAIL,
    }
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(BASE_URL, wait_until="networkidle")
        landing_form = page.locator("[data-landing-context-form]")
        landing_form.wait_for(state="visible")
        landing_form.locator('select[name="landing_sector"]').select_option("Manufactura")
        landing_form.locator('select[name="landing_objective"]').select_option("Preparación para verificación")
        landing_form.locator(".landing-context-submit").click()
        page.wait_for_url("**/diagnostico")
        page.wait_for_load_state("networkidle")

        stored_context = page.evaluate(
            "JSON.parse(window.localStorage.getItem('cth_landing_context_v1') || 'null')"
        )
        if not stored_context or stored_context.get("reusable") != {
            "sector": "Manufactura",
            "objective": "Preparación para verificación",
        }:
            raise AssertionError(f"Contexto de landing inesperado: {stored_context!r}")

        form = page.locator("[data-v260-diagnosis-wizard]")
        form.wait_for(state="visible")
        if form.locator('select[name="sector"]').input_value() != "Manufactura":
            raise AssertionError("El sector seleccionado en landing no llegó al diagnóstico.")
        if form.locator('select[name="objective"]').input_value() != "Preparación para verificación":
            raise AssertionError("El objetivo seleccionado en landing no llegó al diagnóstico.")
        if form.locator("[data-diagnosis-prefill]").count() != 1:
            raise AssertionError("El diagnóstico no confirmó visualmente el contexto reutilizado desde landing.")

        _assert_step(page, 1)
        form.locator('input[name="company_name"]').fill("Funnel Público V2.60.3 S.A.S.")
        form.locator('input[name="contact_name"]').fill("Laura Funnel")
        form.locator('input[name="city"]').fill("Medellín")
        form.locator("[data-diagnosis-next]").click()

        _assert_step(page, 2)
        form.locator('select[name="employees_band"]').select_option("51 a 200")
        form.locator('input[name="facilities_count"]').fill("3")
        form.locator('input[name="countries_count"]').fill("1")
        form.locator('textarea[name="core_processes"]').fill("Producción, almacenamiento, despacho")
        form.locator('input[name="uses_fuels"]').check()
        form.locator('input[name="manages_waste"]').check()
        form.locator('input[name="relies_on_suppliers"]').check()
        form.locator("[data-diagnosis-next]").click()

        _assert_step(page, 3)
        form.locator('select[name="data_availability"]').select_option("Parcial")
        form.locator('select[name="evidence_readiness"]').select_option("Parcial")
        form.locator('select[name="reporting_frequency"]').select_option("Trimestral")
        form.locator('textarea[name="current_data_systems"]').fill("ERP, Excel, SharePoint")
        form.locator("[data-diagnosis-next]").click()

        _assert_step(page, 4)
        if form.locator('select[name="objective"]').input_value() != "Preparación para verificación":
            raise AssertionError("El objetivo preconfigurado cambió antes del envío final.")
        form.locator('select[name="desired_scopes"]').select_option("Alcances 1, 2 y 3 priorizado")
        form.locator('select[name="assurance_ambition"]').select_option("Preparación para verificación limitada")
        form.locator('select[name="deadline_months"]').select_option("6")
        form.locator('select[name="urgency"]').select_option("Normal")
        form.locator('textarea[name="notes"]').fill(
            "Prueba E2E del funnel público con consentimiento explícito y resultado orientativo."
        )
        form.locator('input[name="email"]').fill(EMAIL)
        form.locator('input[name="phone"]').fill("3005556677")
        form.locator('input[name="accept_privacy"]').check()
        form.locator("[data-diagnosis-submit]").click()

        page.wait_for_url("**/diagnostico/gracias/**")
        page.wait_for_load_state("networkidle")
        page.locator("text=DIAGNÓSTICO ORIENTATIVO GENERADO").wait_for(state="visible")
        page.locator("text=Cómo leer estos indicadores").wait_for(state="visible")
        page.locator("text=Preparación de datos").wait_for(state="visible")
        page.locator("text=Decisiones que siguen abiertas").wait_for(state="visible")
        page.locator("text=Gestión Corporativa").wait_for(state="visible")

        result_text = page.locator("main").inner_text()
        for forbidden in (
            "puntos del diagnóstico",
            "horas estimadas",
            "% gobierno del proceso",
            "Gestión Avanzada y Verificación",
        ):
            if forbidden in result_text:
                raise AssertionError(f"El resultado público volvió a exponer semántica interna: {forbidden!r}")

        desktop_logo_state = _canonical_footer_logo_state(page)
        desktop_layout = _assert_no_horizontal_overflow(page, "Resultado desktop")
        screenshot = ARTIFACT_DIR / "public-funnel-result.png"
        page.screenshot(path=str(screenshot), full_page=True)

        result_path = page.url.replace(BASE_URL, "")
        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        page.locator("text=DIAGNÓSTICO ORIENTATIVO GENERADO").wait_for(state="visible")
        page.locator("text=Tu ruta desde este resultado").wait_for(state="visible")
        page.locator("text=Gestión Corporativa").wait_for(state="visible")
        mobile_layout = _assert_no_horizontal_overflow(page, "Resultado móvil")
        mobile_logo_state = _canonical_footer_logo_state(page)
        if page.locator(".result-actions .button").count() < 3:
            raise AssertionError("El resultado móvil perdió alguna de sus tres acciones de salida.")
        mobile_screenshot = ARTIFACT_DIR / "public-funnel-result-mobile.png"
        page.screenshot(path=str(mobile_screenshot), full_page=True)

        evidence["screenshots"] = {
            "desktop": screenshot.name,
            "mobile": mobile_screenshot.name,
        }
        evidence["result_url"] = result_path
        evidence["persistence"] = _persistence_contract()
        evidence["canonical_footer_logo"] = {
            "desktop": desktop_logo_state,
            "mobile": mobile_logo_state,
        }
        evidence["layout"] = {
            "desktop": desktop_layout,
            "mobile": mobile_layout,
        }
        evidence["browser_errors"] = {"console": console_errors, "page": page_errors}

        if console_errors or page_errors:
            raise AssertionError(
                f"Errores de navegador durante el funnel público: console={console_errors}, page={page_errors}"
            )

        context.close()
        browser.close()

    evidence_path = ARTIFACT_DIR / "public-funnel-gate.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
