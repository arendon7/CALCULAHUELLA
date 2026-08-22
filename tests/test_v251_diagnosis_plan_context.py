from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "app" / "templates" / "public" / "v15" / "pricing_about.html"
DIAGNOSIS = ROOT / "app" / "templates" / "public_diagnosis.html"
THANKS = ROOT / "app" / "templates" / "public_thanks.html"
PLAN_COPY = ROOT / "app" / "templates" / "public" / "plan_copy.html"
HANDOFF = ROOT / "app" / "static" / "js" / "diagnosis_handoff.js"
ENGINE = ROOT / "app" / "product_intelligence_web.py"
SEED_DEFAULTS = ROOT / "app" / "seed_defaults.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v251_pricing_ctas_carry_only_canonical_plan_codes() -> None:
    pricing = _text(PRICING)
    for code in ("ESENCIAL", "EMPRESARIAL", "CORPORATIVO"):
        assert f'href="/diagnostico?plan={code}"' in pricing
    assert "plan_label=" not in pricing
    assert "recommended_plan=" not in pricing


def test_v251_diagnosis_handoff_treats_plan_as_visual_reference_only() -> None:
    handoff = _text(HANDOFF)
    for code, label in (
        ("ESENCIAL", "Huella Esencial"),
        ("EMPRESARIAL", "Huella Empresarial"),
        ("CORPORATIVO", "Gestión Corporativa"),
    ):
        assert f"{code}: '{label}'" in handoff
    assert "new URLSearchParams(window.location.search)" in handoff
    assert "params.get('plan')" in handoff
    assert "referencia comercial, no una decisión del motor" in handoff
    assert "el diagnóstico puede recomendar otro nivel" in handoff.lower()
    assert "createElement('input')" not in handoff
    assert "evaluated_plan" not in handoff

    diagnosis = _text(DIAGNOSIS)
    assert 'action="/diagnostico" method="post"' in diagnosis
    assert 'name="plan"' not in diagnosis
    assert 'name="evaluated_plan"' not in diagnosis


def test_v251_incoming_plan_cannot_override_engine_recommendation() -> None:
    engine = _text(ENGINE)
    assert "recommended_plan_code=provisional.recommended_package_code" in engine
    assert 'plan: str = Form(' not in engine
    assert 'recommended_plan_code=plan' not in engine


def test_v251_public_result_uses_current_public_plan_presentation_truth() -> None:
    thanks = _text(THANKS)
    plan_copy = _text(PLAN_COPY)

    assert 'from "public/plan_copy.html" import public_plan_description, public_plan_name' in thanks
    assert "public_plan_name(lead.recommended_plan_code)" in thanks
    assert "{{ public_plan_description(lead.recommended_plan_code) }}" in thanks
    assert "assessment.package_label" not in thanks
    assert "assessment.package_description" not in thanks
    assert "plan.description" not in thanks

    for code, label in (
        ("ESENCIAL", "Huella Esencial"),
        ("EMPRESARIAL", "Huella Empresarial"),
        ("CORPORATIVO", "Gestión Corporativa"),
    ):
        assert code in plan_copy
        assert label in plan_copy

    seed = _text(SEED_DEFAULTS)
    assert '("ESENCIAL", "Huella Esencial"' in seed
    assert '("EMPRESARIAL", "Huella Empresarial"' in seed
    assert '("CORPORATIVO", "Gestión Corporativa"' in seed
