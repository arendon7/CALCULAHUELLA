from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def read_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_guided_styles_are_loaded_from_frontend_kit_layer():
    token_css = (STATIC / "css" / "cth-tokens.css").read_text(encoding="utf-8")
    guided_css = (STATIC / "css" / "cth-guided.css").read_text(encoding="utf-8")

    assert '@import "./cth-guided.css";' in token_css
    assert ".onboarding-command" in guided_css
    assert ".onboarding-stage.current" in guided_css
    assert ".inventory-wizard" in guided_css
    assert '.inventory-wizard-nav > button[aria-current="step"]' in guided_css
    assert ".starter-pack-choice input:checked + .starter-pack-body" in guided_css
    assert "@media (max-width: 560px)" in guided_css


def test_onboarding_exposes_progress_next_action_and_current_stage():
    onboarding = read_template("onboarding.html")

    assert 'aria-labelledby="onboarding-command-title"' in onboarding
    assert 'role="progressbar"' in onboarding
    assert 'aria-valuenow="{{ onboarding.score }}"' in onboarding
    assert 'aria-label="Resumen de actividades"' in onboarding
    assert 'aria-labelledby="onboarding-roadmap-title"' in onboarding
    assert 'aria-current="step"' in onboarding
    assert "Abrir siguiente actividad:" in onboarding


def test_inventory_wizard_connects_steps_and_accessible_progress():
    inventory = read_template("inventory_form.html")
    base = read_template("base.html")
    guided_js = (STATIC / "js" / "cth-guided.js").read_text(encoding="utf-8")

    assert 'aria-labelledby="inventory-wizard-title"' in inventory
    assert 'aria-controls="inventory-step-1"' in inventory
    assert 'aria-controls="inventory-step-4"' in inventory
    assert 'data-inventory-progress-container role="progressbar"' in inventory
    assert 'aria-valuetext="Paso 1 de 4"' in inventory
    assert 'aria-live="polite"' in inventory
    assert 'id="inventory-step-1"' in inventory
    assert 'id="inventory-step-4"' in inventory
    assert 'tabindex="-1"' in inventory

    assert "js/cth-guided.js" in base
    assert "MutationObserver" in guided_js
    assert "aria-valuenow" in guided_js
    assert "aria-valuetext" in guided_js
    assert "aria-expanded" in guided_js
