from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "api" / "index.py"
VERCEL = ROOT / "vercel.json"


def test_vercel_staging_adapter_is_explicitly_non_production():
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert 'os.environ.setdefault("APP_ENV", "staging")' in text
    assert 'os.environ.setdefault("INSTANCE_DIR", str(INSTANCE_DIR))' in text
    assert 'Path("/tmp/calcula-tu-huella")' in text
    assert 'os.environ.setdefault("SCHEDULER_ENABLED", "false")' in text
    assert 'os.environ.setdefault("DEPLOYMENT_STRICT", "false")' in text
    assert 'os.environ.setdefault("STORAGE_BACKEND", "local")' in text
    assert 'os.environ.setdefault("EMAIL_BACKEND", "disabled")' in text
    assert 'from app.main import app' in text


def test_vercel_adapter_does_not_embed_database_or_provider_secrets():
    text = ENTRYPOINT.read_text(encoding="utf-8")
    forbidden = (
        "postgresql://",
        "postgresql+psycopg://",
        "supabase.co",
        "S3_ACCESS_KEY=",
        "S3_SECRET_KEY=",
        "SMTP_PASSWORD=",
    )
    for token in forbidden:
        assert token not in text


def test_vercel_routes_all_requests_to_fastapi_entrypoint():
    text = VERCEL.read_text(encoding="utf-8")
    assert '"api/index.py"' in text
    assert '"destination": "/api/index.py"' in text
    assert '"maxDuration": 60' in text
