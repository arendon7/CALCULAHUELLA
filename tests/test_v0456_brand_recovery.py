import base64
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "brand" / "extract_embedded_master.py"

spec = importlib.util.spec_from_file_location("extract_embedded_master", MODULE_PATH)
assert spec and spec.loader
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)

# PNG transparent 1 × 1, usado únicamente como fixture técnico de prueba.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def html_with_png(data: bytes, alt: str = "Calcula tu Huella") -> str:
    payload = base64.b64encode(data).decode("ascii")
    return f'<html><body><img alt="{alt}" src="data:image/png;base64,{payload}"></body></html>'


def test_recovers_identical_logo_copies_from_multiple_html_files(tmp_path):
    first = tmp_path / "v0_44_experiencia.html"
    second = tmp_path / "experiencia_interna.html"
    first.write_text(html_with_png(PNG_1X1), encoding="utf-8")
    second.write_text(html_with_png(PNG_1X1), encoding="utf-8")

    selected, data, candidates = recovery.select_exact_copy([first, second], 1, 1)

    assert data == PNG_1X1
    assert selected.width == 1
    assert selected.height == 1
    assert len(candidates) == 2
    assert len({candidate.sha256 for candidate in candidates}) == 1


def test_rejects_truncated_base64(tmp_path):
    source = tmp_path / "truncated.html"
    source.write_text(
        '<img alt="Calcula tu Huella" src="data:image/png;base64,iVBORw0KGgo">',
        encoding="utf-8",
    )

    with pytest.raises(recovery.EmbeddedLogoError):
        recovery.select_exact_copy([source], 1, 1)


def test_rejects_non_matching_dimensions(tmp_path):
    source = tmp_path / "other-size.html"
    source.write_text(html_with_png(PNG_1X1), encoding="utf-8")

    with pytest.raises(recovery.EmbeddedLogoError, match="No existe una copia"):
        recovery.select_exact_copy([source], 470, 195)


def test_recovery_script_does_not_contain_image_transformation_operations():
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = ("resize(", "thumbnail(", "crop(", "convert(", "ImageEnhance", "recolor")
    assert not any(token in source for token in forbidden)
    assert '"transformation": "none"' in source
