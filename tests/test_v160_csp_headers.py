from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _directives(policy: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in policy.split(";"):
        part = raw.strip()
        if not part:
            continue
        name, *rest = part.split(None, 1)
        parsed[name] = rest[0] if rest else ""
    return parsed


def test_csp3_real_response_separates_element_and_attribute_styles() -> None:
    with TestClient(app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    directives = _directives(policy)

    assert directives["default-src"] == "'self'"
    assert directives["script-src"] == "'self'"
    assert directives["style-src"] == "'self'"
    assert directives["style-src-elem"] == "'self'"
    assert directives["style-src-attr"] == "'unsafe-inline'"
    assert "'unsafe-eval'" not in policy
    assert policy.count("'unsafe-inline'") == 1
