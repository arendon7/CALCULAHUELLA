from pathlib import Path


PUBLIC_WEB = Path("app/public_web.py")
PUBLIC_CONTACT = Path("app/templates/public_contact.html")
PUBLIC_BASE = Path("app/templates/public_base.html")
PAGES_SECTION = Path("site/sections/experience-resources-diagnostic.html")
PAGES_RUNTIME = Path("site/route-handoff-runtime.js")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pages_never_collects_contact_pii_or_posts_cross_origin() -> None:
    section = _text(PAGES_SECTION)
    runtime = _text(PAGES_RUNTIME)

    for forbidden in (
        'name="company_name"',
        'name="contact_name"',
        'name="email"',
        'name="phone"',
        'name="accept_privacy"',
        "data-route-contact-form",
    ):
        assert forbidden not in section

    assert "contactForm" not in runtime
    assert ".method = 'post'" not in runtime
    assert ".action =" not in runtime
    assert "new URL(`${appBaseUrl}/contacto`)" in runtime
    assert "searchParams.set('plan'" in runtime
    assert "searchParams.set('sector'" in runtime
    assert "searchParams.set('sites'" in runtime
    assert "searchParams.set('objective'" in runtime


def test_contact_pii_is_collected_only_same_origin_with_existing_csrf_contract() -> None:
    public_web = _text(PUBLIC_WEB)
    template = _text(PUBLIC_CONTACT)
    base = _text(PUBLIC_BASE)

    assert '@app.get("/contacto", response_class=HTMLResponse)' in public_web
    assert '@app.post("/contacto")' in public_web
    assert 'method="post" action="/contacto"' in template
    assert 'name="_csrf_token" value="{{ request.state.csrf_token }}"' in template
    assert 'name="company_name"' in template
    assert 'name="contact_name"' in template
    assert 'name="email"' in template
    assert 'name="phone"' in template
    assert 'name="accept_privacy" value="yes" required' in template
    assert 'href="/legal/privacidad"' in template
    assert "public-contact.css" in base


def test_pages_context_is_whitelisted_again_by_backend() -> None:
    public_web = _text(PUBLIC_WEB)

    assert "_ALLOWED_CONTACT_PLANS" in public_web
    assert "_ALLOWED_SECTORS" in public_web
    assert "_ALLOWED_OBJECTIVES" in public_web
    assert '_query_choice(request, "plan"' in public_web
    assert '_query_choice(request, "sector"' in public_web
    assert '_query_sites(request)' in public_web
    assert '_query_choice(request, "objective"' in public_web
    assert '"Gestión Avanzada": "CORPORATIVO"' in public_web
