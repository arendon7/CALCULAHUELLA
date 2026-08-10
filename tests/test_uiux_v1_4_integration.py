from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def public_runtime_corpus() -> str:
    return "\n".join(
        read(path)
        for path in (
            "app/templates/public_base.html",
            "app/templates/public_home.html",
        )
    )


def test_v14_css_preserves_canonical_layer():
    entry = read("app/static/css/app.css")
    assert '@import url("./app-canonical-v1.css")' in entry
    assert "V1.4.0 integración controlada" in entry
    assert (ROOT / "app/static/css/app-canonical-v1.css").exists()


def test_v14_public_runtime_uses_real_routes():
    corpus = public_runtime_corpus()
    assert "Toda tu gestión de carbono" in corpus
    assert 'href="/diagnostico"' in corpus
    assert 'href="/login"' in corpus
    assert "demo_funcional.html" not in corpus
    assert "localhost" not in corpus.lower()
    assert "public-v1.6.css" in corpus
    assert "public-v1.6.js" in corpus
    assert "public-v1.4.css" not in corpus
    assert "public-v1.4.js" not in corpus


def test_v14_static_site_is_self_consistent():
    html = read("site/index.html")
    assert "styles.css" in html and "app.js" in html and "config.js" in html
    assert "demo_funcional.html" not in html
    assert "127.0.0.1" not in html
    assert "localhost" not in html.lower()
    assert (ROOT / "site/assets/logo.svg").exists()


def test_v14_claims_keep_methodological_reserve():
    corpus = public_runtime_corpus().lower()
    assert "no actúa automáticamente como organismo verificador o certificador" in corpus
    assert "certificación automática" not in corpus
