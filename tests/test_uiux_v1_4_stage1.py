from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "app" / "static" / "css"


def test_v14_css_entry_is_reversible():
    entry = (CSS / "app.css").read_text(encoding="utf-8")
    assert '@import url("./app-canonical-v1.css")' in entry
    assert '@import url("./v1.4.css")' in entry
    assert (CSS / "app-canonical-v1.css").exists()
    assert (CSS / "v1.4.css").exists()


def test_v14_does_not_embed_remote_or_localhost_dependencies():
    override = (CSS / "v1.4.css").read_text(encoding="utf-8")
    forbidden = ("localhost", "127.0.0.1", "http://", "https://")
    assert not any(token in override for token in forbidden)
