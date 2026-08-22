from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "design" / "WEB_DESIGN_SKILL_REGISTRY.json"


@pytest.mark.smoke
def test_web_design_governance_contract_is_valid() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/design/check_web_design_governance.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "WEB DESIGN GOVERNANCE PASS" in result.stdout


@pytest.mark.smoke
def test_product_ui_does_not_delegate_to_taste_as_primary() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    product_ui = registry["routing"]["product_ui"]
    assert "design-taste-frontend" not in product_ui["primary"]
    assert "design-taste-frontend" in product_ui["restricted"]


@pytest.mark.smoke
def test_external_skills_are_pinned_and_not_auto_updated() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["upstream_policy"]["automatic_updates"] is False
    assert all(len(source["reviewed_commit"]) == 40 for source in registry["sources"])
