import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "brand" / "verify_master_assets.py"
MANIFEST_PATH = ROOT / "app" / "static" / "img" / "brand-manifest.json"
PRIMARY = ROOT / "app" / "static" / "img" / "brand-primary.svg"
SYMBOL = ROOT / "app" / "static" / "img" / "brand-symbol.svg"

spec = importlib.util.spec_from_file_location("v210_verify_brand", VERIFIER_PATH)
assert spec and spec.loader
verifier = importlib.util.module_from_spec(spec)
sys.modules["v210_verify_brand"] = verifier
spec.loader.exec_module(verifier)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_is_anchored_to_later_v142_classic_brand_decision():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    approved = manifest["approved_master"]

    assert manifest["system"] == "Identidad canónica · logo clásico"
    assert approved["status"] == "installed_exact_classic"
    assert approved["decision_version"] == "1.4.2"
    assert approved["decision_date"] == "2026-08-06"
    assert approved["redraw_allowed"] is False
    assert approved["placeholder_allowed"] is False
    assert approved["variants_allowed"] is False
    assert set(approved["assets"]) == {"logo_primary", "symbol"}
    verifier.validate_manifest(manifest)


def test_primary_and_symbol_match_authoritative_sha256_byte_for_byte():
    assert PRIMARY.stat().st_size == 1484
    assert digest(PRIMARY) == "04a9b2557c1aff819eef52364dbe88677044299a6c868a7318703fdccffa638e"
    assert SYMBOL.stat().st_size == 855
    assert digest(SYMBOL) == "c43e33c89860aac5d7f582009b7d53e7902aa7704c9484fefcb1e2a2f99ce3e8"
    verifier.validate_exact_files()


def test_canonical_svg_bytes_keep_historical_accessible_metadata_and_no_newline_drift():
    primary = PRIMARY.read_bytes()
    symbol = SYMBOL.read_bytes()

    assert not primary.endswith(b"\n")
    assert not symbol.endswith(b"\n")
    assert b'aria-label="Calcula tu Huella"' in primary
    assert 'aria-label="Símbolo Calcula tu Huella"'.encode("utf-8") in symbol


def test_exact_brand_verifier_is_strict_by_default():
    verifier.validate()


def test_obsolete_png_master_contract_is_not_reintroduced():
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    forbidden = (
        "recoverable_exact_primary_from_embedded_html",
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
        "C circular envolvente",
    )
    assert not any(token in manifest_text for token in forbidden)
