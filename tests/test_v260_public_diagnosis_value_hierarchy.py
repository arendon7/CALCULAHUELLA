from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = ROOT / "app" / "templates" / "public_diagnosis.html"
RESULT = ROOT / "app" / "templates" / "public_thanks.html"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v260_public_diagnosis_avoids_unproven_timing_and_immediacy_claims() -> None:
    diagnosis = _text(DIAGNOSIS)

    assert "En unos minutos" in diagnosis
    assert "Resultado orientativo al finalizar" in diagnosis
    assert "4–6 minutos" not in diagnosis
    assert "Resultado inmediato" not in diagnosis
    assert "No calcula tu huella" in diagnosis
    assert "no certifica resultados" in diagnosis
    assert "no reemplaza la revisión del equipo técnico" in diagnosis


def test_v260_public_result_puts_diagnostic_value_before_commercial_recommendation() -> None:
    result = _text(RESULT)

    diagnostic_markers = (
        "Complejidad operativa",
        "Madurez general",
        "Madurez de datos",
        "Preparación para revisión externa",
        "Qué sabemos ahora",
        "Qué conviene validar",
        "Configuración sugerida",
        "Tu ruta desde este resultado",
    )
    for marker in diagnostic_markers:
        assert marker in result

    commercial_markers = (
        "Referencia comercial, después del diagnóstico",
        "Plan de referencia",
        "Tiempo inicial de referencia",
    )
    for marker in commercial_markers:
        assert marker in result

    plan_position = result.index("Plan de referencia")
    for marker in diagnostic_markers:
        assert result.index(marker) < plan_position

    assert "Paquete recomendado" not in result
    assert "Implementación estimada" not in result


def test_v260_public_result_does_not_present_assessment_as_footprint_or_verification() -> None:
    result = _text(RESULT)

    assert "DIAGNÓSTICO ORIENTATIVO GENERADO" in result
    assert "DIAGNÓSTICO INTELIGENTE GENERADO" not in result
    assert "No es una huella calculada, una certificación ni una verificación independiente" in result
    assert "Indicador orientativo; no equivale a una verificación" in result
    assert "No constituye una cotización definitiva" in result
    assert "sujeta a validación técnica del alcance" in result


def test_v260_result_uses_existing_assessment_signals_without_new_calculation_logic() -> None:
    result = _text(RESULT)

    assert "assessment.row.complexity_level" in result
    assert "assessment.row.maturity_level" in result
    assert "assessment.row.governance_maturity_score" in result
    assert "assessment.row.data_maturity_score" in result
    assert "assessment.row.verification_readiness_score" in result
    assert "assessment.recommended_scopes" in result
    assert "assessment.probable_sources" in result
    assert "assessment.findings" in result
    assert "assessment.risk_flags" in result
    assert "assessment.applicable_modules" in result
    assert "assessment.exclusions" in result
    assert "assessment.next_steps" in result
