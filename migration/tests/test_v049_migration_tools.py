from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_v049_tools_delegate_to_current_release_contract():
    verifier = (ROOT / "scripts/migration/verify_v049_archive.py").read_text(encoding="utf-8")
    importer = (ROOT / "scripts/migration/import_v049_archive.py").read_text(encoding="utf-8")
    contract = (ROOT / "migration/v0.49.0-contract.json").read_text(encoding="utf-8")

    assert "verify_current_release.py" in verifier
    assert "import_current_release.py" in importer
    assert "superseded_historical_reference" in contract
    assert "migration/current-release.json" in contract
