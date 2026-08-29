from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "app" / "templates" / "public" / "v15" / "product_proof.html"


def _proof() -> str:
    return PROOF.read_text(encoding="utf-8")


def test_v250_product_proof_explains_operational_value_not_only_screen_names() -> None:
    proof = _proof()
    assert "No solo calcula: hace visible qué falta, quién actúa y con qué evidencia." in proof
    for label in (
        "01 · PRIORIZAR",
        "02 · RESPALDAR",
        "03 · GOBERNAR",
        "04 · ALINEAR",
        "05 · SEGUIR",
    ):
        assert label in proof

    for outcome in (
        "qué está frenando el inventario y cuál es la siguiente acción",
        "los vacíos queden visibles antes de avanzar con cálculo y revisión",
        "cada etapa tenga contexto y una siguiente acción comprensible",
        "reducir interpretaciones distintas",
        "facilitar seguimiento cuando el equipo no está frente al escritorio",
    ):
        assert outcome in proof


def test_v250_product_proof_preserves_real_assets_demo_boundary_and_method_authority() -> None:
    proof = _proof()
    for filename in ("dashboard.png", "captura.png", "recorrido.png", "diccionario.png", "movil.png"):
        assert f"img/product-proof/{filename}" in proof

    assert "Los datos visibles son demostrativos" in proof
    assert "La interfaz sigue evolucionando." in proof
    assert "La autoridad del cálculo permanece en datos, factores, fórmulas, evidencias y decisiones trazables." in proof
    assert 'href="/login"' in proof


def test_v250_product_proof_remains_read_only_and_does_not_add_external_dependencies() -> None:
    proof = _proof().lower()
    assert "<form" not in proof
    assert 'method="post"' not in proof
    assert "http://" not in proof
    assert "https://" not in proof
