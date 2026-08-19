from pathlib import Path

from app.public_web import _normalize_contact_plan


PUBLIC_WEB = Path("app/public_web.py")
CONTACT = Path("app/templates/public_contact.html")
PAGES_RUNTIME = Path("site/route-handoff-runtime.js")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v254_legacy_and_current_plan_labels_resolve_to_current_public_names():
    cases = {
        "Huella Esencial": ("ESENCIAL", "Huella Esencial"),
        "Huella Empresarial": ("EMPRESARIAL", "Huella Empresarial"),
        "Gestión Corporativa": ("CORPORATIVO", "Gestión Corporativa"),
        "Gestión de Carbono": ("EMPRESARIAL", "Huella Empresarial"),
        "Gestión Avanzada": ("CORPORATIVO", "Gestión Corporativa"),
        "Gestión Avanzada y Verificación": ("CORPORATIVO", "Gestión Corporativa"),
    }
    for incoming, expected in cases.items():
        assert _normalize_contact_plan(incoming) == expected


def test_v254_unknown_plan_values_remain_rejected():
    assert _normalize_contact_plan("") == ("", "")
    assert _normalize_contact_plan("CORPORATIVO") == ("", "")
    assert _normalize_contact_plan("Plan inventado") == ("", "")


def test_v254_get_and_post_use_same_whitelist_and_canonical_code():
    public_web = _text(PUBLIC_WEB)

    assert 'raw_plan = _query_choice(request, "plan", _ALLOWED_CONTACT_PLANS)' in public_web
    assert '_, current_plan_label = _normalize_contact_plan(raw_plan)' in public_web
    assert '"plan": current_plan_label' in public_web
    assert 'if normalized_interest not in _ALLOWED_CONTACT_PLANS:' in public_web
    assert 'plan_code, current_plan_label = _normalize_contact_plan(normalized_interest)' in public_web
    assert 'recommended_plan_code=plan_code' in public_web


def test_v254_contact_handoff_does_not_expand_query_or_pii_surface():
    runtime = _text(PAGES_RUNTIME)
    contact = _text(CONTACT)

    for key in ("plan", "sector", "sites", "objective"):
        assert f"searchParams.set('{key}'" in runtime
    for forbidden in ("company_name", "contact_name", "email", "phone"):
        assert f"searchParams.set('{forbidden}'" not in runtime

    assert 'name="interest" value="{{ route_context.plan }}"' in contact
    assert 'name="sector" value="{{ route_context.sector }}"' in contact
