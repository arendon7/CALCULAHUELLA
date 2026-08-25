from pathlib import Path

from app.public_result_access import public_result_access_window_label


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "app/templates/public_thanks.html"
UNAVAILABLE = ROOT / "app/templates/public_result_unavailable.html"
ROUTES = ROOT / "app/product_intelligence_web.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v258_access_window_label_tracks_configuration_units():
    assert public_result_access_window_label(720) == "30 días"
    assert public_result_access_window_label(24) == "1 día"
    assert public_result_access_window_label(36) == "36 horas"
    assert public_result_access_window_label(1) == "1 hora"


def test_v258_result_explains_link_expiry_without_claiming_data_deletion():
    result = _read(RESULT)

    assert "enlace público" in result
    assert "vigencia limitada" in result
    assert "{{ public_result_access_window }}" in result
    assert "no significa que el registro se elimine" in result
    assert "Este resultado no crea una cuenta ni activa una licencia por sí solo" in result


def test_v258_unavailable_result_is_generic_noindex_and_recoverable():
    unavailable = _read(UNAVAILABLE)

    assert 'noindex,nofollow,noarchive' in unavailable
    assert "Este resultado no está disponible" in unavailable
    assert "puede haber vencido o no ser válido" in unavailable
    assert "no distinguimos entre ambos casos" in unavailable
    assert 'href="/diagnostico"' in unavailable
    assert 'href="/"' in unavailable
    assert "lead." not in unavailable
    assert "token" not in unavailable.casefold()


def test_v258_missing_and_expired_links_share_the_same_404_surface():
    routes = _read(ROUTES)
    public_result_route = routes.split(
        '@app.get("/diagnostico/gracias/{token}", response_class=HTMLResponse)', 1
    )[1].split('@app.get("/inteligencia-producto", response_class=HTMLResponse)', 1)[0]

    assert "if not lead or public_result_is_expired(" in public_result_route
    assert 'name="public_result_unavailable.html"' in public_result_route
    assert "status_code=404" in public_result_route
    assert 'raise HTTPException(404, "Diagnóstico no encontrado")' not in public_result_route
    assert '"public_result_access_window": public_result_access_window_label(' in public_result_route
