from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_csrf_middleware_exposes_same_request_token_to_templates() -> None:
    source = (ROOT / "app" / "security.py").read_text(encoding="utf-8")
    assert 'scope.setdefault("state", {})["csrf_token"] = token' in source
    assert 'supplied = headers.get(CSRF_HEADER, "") or _csrf_form_value' in source
    assert "hmac.compare_digest(supplied, token)" in source


def test_supplier_portal_posts_server_rendered_csrf_token() -> None:
    template = (ROOT / "app" / "templates" / "supplier_portal.html").read_text(encoding="utf-8")
    assert 'name="_csrf_token"' in template
    assert 'value="{{ request.state.csrf_token }}"' in template
    assert 'action="/proveedor/responder/{{ data_request.access_token }}"' in template


def test_supplier_portal_is_not_exempted_from_csrf_middleware() -> None:
    source = (ROOT / "app" / "security.py").read_text(encoding="utf-8")
    assert 'path.startswith("/proveedor/")' not in source
    assert 'path.startswith("/api/")' in source
