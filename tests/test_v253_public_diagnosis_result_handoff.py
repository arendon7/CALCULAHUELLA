from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "app/templates/public/v15/pricing_about.html"
RESULT = ROOT / "app/templates/public_thanks.html"
PUBLIC_BASE = ROOT / "app/templates/public_base.html"
PLAN_COPY = ROOT / "app/templates/public/plan_copy.html"
PRODUCT_INTELLIGENCE_WEB = ROOT / "app/product_intelligence_web.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v253_public_plan_copy_is_shared_and_verification_safe():
    pricing = _read(PRICING)
    result = _read(RESULT)
    copy = _read(PLAN_COPY)

    assert 'from "public/plan_copy.html" import public_plan_description, public_plan_fit' in pricing
    assert 'from "public/plan_copy.html" import public_plan_description, public_plan_name' in result
    assert "{{ public_plan_description(plan.code) }}" in pricing
    assert "{{ public_plan_description(lead.recommended_plan_code) }}" in result

    for code in ("ESENCIAL", "EMPRESARIAL", "CORPORATIVO"):
        assert code in copy
    assert "Huella Esencial" in copy
    assert "Huella Empresarial" in copy
    assert "Gestión Corporativa" in copy
    assert "verific" not in copy.casefold()


def test_v253_public_result_does_not_render_raw_internal_or_service_plan_descriptions():
    result = _read(RESULT)

    assert "plan.description" not in result
    assert "assessment.package_description" not in result
    assert "assessment.package_label" not in result
    assert "Gestión Avanzada y Verificación" not in result
    assert "Gestión de Carbono" not in result


def test_v253_result_handoff_does_not_present_login_as_the_next_commercial_step():
    result = _read(RESULT)
    actions = result.split('<div class="result-actions">', 1)[1].split("</div>", 1)[0]

    assert "Tu diagnóstico quedó registrado." in result
    assert "no crea una cuenta ni activa una licencia por sí solo" in result
    assert 'href="/#precios"' in actions
    assert 'href="/login"' not in actions
    assert 'href="/login"' in result
    assert "¿Ya tienes una cuenta?" in result


def test_v253_individual_result_is_noindex_while_public_base_keeps_default_indexing():
    base = _read(PUBLIC_BASE)
    result = _read(RESULT)

    assert '{% block robots %}<meta name="robots" content="index,follow">{% endblock %}' in base
    assert '{% block robots %}<meta name="robots" content="noindex,nofollow,noarchive">{% endblock %}' in result


def test_v253_result_keeps_recommendation_authority_in_the_diagnostic_engine():
    routes = _read(PRODUCT_INTELLIGENCE_WEB)

    assert "recommended_plan_code=provisional.recommended_package_code" in routes
    assert 'source="Diagnóstico inteligente V0.45"' in routes


def test_v253_findings_and_risks_are_separate_valid_lists():
    result = _read(RESULT)

    findings = '<ul>{% for item in assessment.findings %}<li>{{ item }}</li>{% endfor %}</ul>'
    risks = '<ul>{% for item in assessment.risk_flags %}<li>{{ item }}</li>{% endfor %}</ul>'
    assert findings in result
    assert risks in result
    assert findings in result.split("<h2>Hallazgos iniciales</h2>", 1)[1]
