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


def test_vercel_adapter_does_not_embed_provider_credentials():
    text = ENTRYPOINT.read_text(encoding="utf-8")
    forbidden = (
        "supabase.co",
        "S3_ACCESS_KEY=",
        "S3_SECRET_KEY=",
        "SMTP_PASSWORD=",
        "DATABASE_URL=postgres",
    )
    for token in forbidden:
        assert token not in text
    # Los nombres de esquema son necesarios para normalizar connection strings
    # inyectadas por el proveedor; no constituyen una credencial embebida.
    assert 'startswith("postgresql://")' in text
    assert 'startswith("postgres://")' in text


def test_external_database_never_bootstraps_schema_at_import_time():
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert 'EXPECTED_EXTERNAL_ALEMBIC_REVISION = "20260812_0040"' in text
    assert "SELECT version_num FROM alembic_version LIMIT 1" in text
    assert "if revision != EXPECTED_EXTERNAL_ALEMBIC_REVISION" in text
    external_block = text.split("if _external_database:", 1)[1].split("else:", 1)[0]
    assert "init_db" not in external_block
    ephemeral_block = text.split("else:", 1)[1]
    assert "init_db()" in ephemeral_block


def test_vercel_routes_all_requests_to_fastapi_entrypoint():
    text = VERCEL.read_text(encoding="utf-8")
    assert '"api/index.py"' in text
    assert '"destination": "/api/index.py"' in text
    assert '"maxDuration": 60' in text
