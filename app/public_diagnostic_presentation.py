from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicDiagnosticInterpretation:
    """Presentation-only interpretation of heuristic diagnostic outputs.

    Exact scores remain owned by the product-intelligence engine and persistence
    layer. This view deliberately converts them to coarse public bands so the
    public result cannot be mistaken for an audit score, compliance percentage
    or independent assurance conclusion.
    """

    data_readiness: str
    review_readiness: str
    duration_reference: str


def data_readiness_band(score: int) -> str:
    value = max(0, min(int(score), 100))
    if value >= 80:
        return "Alta"
    if value >= 60:
        return "Media"
    if value >= 40:
        return "En desarrollo"
    return "Inicial"


def review_readiness_band(score: int) -> str:
    value = max(0, min(int(score), 100))
    if value >= 70:
        return "Preparación alta"
    if value >= 50:
        return "En desarrollo"
    return "Inicial"


def duration_reference(months: int) -> str:
    """Return a deliberately ranged planning reference, never an SLA."""

    value = max(1, int(months))
    return f"{value}–{value + 1} meses"


def build_public_diagnostic_interpretation(
    *,
    data_maturity_score: int,
    verification_readiness_score: int,
    estimated_duration_months: int,
) -> PublicDiagnosticInterpretation:
    return PublicDiagnosticInterpretation(
        data_readiness=data_readiness_band(data_maturity_score),
        review_readiness=review_readiness_band(verification_readiness_score),
        duration_reference=duration_reference(estimated_duration_months),
    )
