from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = ROOT / "app" / "templates" / "public_diagnosis.html"
ENGINE = ROOT / "app" / "product_intelligence_web.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _step(template: str, number: int) -> str:
    marker = f'data-diagnosis-step="{number}"'
    start = template.index(marker)
    if number < 4:
        end = template.index(f'data-diagnosis-step="{number + 1}"', start)
    else:
        end = template.index('class="diagnosis-wizard-actions"', start)
    return template[start:end]


def test_v252_contact_channels_are_deferred_until_final_step() -> None:
    diagnosis = _text(DIAGNOSIS)
    first = _step(diagnosis, 1)
    final = _step(diagnosis, 4)

    assert 'name="company_name"' in first
    assert 'name="contact_name"' in first
    assert 'name="sector"' in first
    assert 'name="city"' in first
    assert 'name="email"' not in first
    assert 'name="phone"' not in first

    assert 'type="email" name="email"' in final
    assert 'name="phone"' in final
    assert "El correo se solicita únicamente al completar el diagnóstico." in diagnosis


def test_v252_progressive_contact_keeps_same_post_contract_and_required_identity() -> None:
    diagnosis = _text(DIAGNOSIS)
    assert 'action="/diagnostico" method="post"' in diagnosis
    assert 'name="company_name"' in diagnosis
    assert 'name="contact_name"' in diagnosis

    email_input = next(line for line in diagnosis.splitlines() if 'name="email"' in line)
    assert 'type="email"' in email_input
    assert 'autocomplete="email"' in email_input
    assert "fv.get('email', '')" in email_input
    assert "required" in email_input
    assert diagnosis.count('name="email"') == 1
    assert diagnosis.count('name="phone"') == 1

    engine = _text(ENGINE)
    for field in ("company_name", "contact_name", "email", "phone"):
        assert f"{field}: str = Form(" in engine


def test_v252_does_not_change_four_step_technical_sequence_or_method_boundary() -> None:
    diagnosis = _text(DIAGNOSIS)
    for number, title in (
        (1, "Empresa y contacto"),
        (2, "Escala y operación"),
        (3, "Datos y madurez"),
        (4, "Objetivo y profundidad"),
    ):
        assert f'data-diagnosis-step="{number}"' in diagnosis
        assert f"<h2>{title}</h2>" in diagnosis

    assert "Una orientación inicial, no una verificación" in diagnosis
    assert "No calcula tu huella" in diagnosis
    assert "no certifica resultados" in diagnosis
    assert "no reemplaza la revisión del equipo técnico" in diagnosis
    assert "No necesitas adjuntar documentos ni cifras de emisiones" in diagnosis
