from __future__ import annotations

from collections.abc import Iterable
from typing import Any

ACCOUNTING_TREATMENTS = (
    "Emisión bruta",
    "CO₂ biogénico informativo",
    "Remoción",
    "Emisión evitada",
    "Compensación",
)
SCOPE2_METHODS = ("No aplica", "Location-based", "Market-based")


def treatment_for(source: Any) -> str:
    value = str(getattr(source, "accounting_treatment", "") or "Emisión bruta")
    return value if value in ACCOUNTING_TREATMENTS else "Emisión bruta"


def is_gross_source(source: Any) -> bool:
    return bool(getattr(source, "included", True)) and treatment_for(source) == "Emisión bruta"


def balance_from_sources(sources: Iterable[Any]) -> dict[str, float]:
    totals = {key: 0.0 for key in ACCOUNTING_TREATMENTS}
    for source in sources:
        if not getattr(source, "included", True):
            continue
        totals[treatment_for(source)] += float(getattr(source, "emissions", 0) or 0)
    gross = totals["Emisión bruta"]
    removals = abs(totals["Remoción"])
    return {
        "gross_emissions": round(gross, 6),
        "biogenic_memo": round(totals["CO₂ biogénico informativo"], 6),
        "removals": round(removals, 6),
        "net_after_removals": round(gross - removals, 6),
        "avoided_emissions": round(totals["Emisión evitada"], 6),
        "offsets": round(totals["Compensación"], 6),
        "net_after_offsets": round(gross - removals - totals["Compensación"], 6),
    }
