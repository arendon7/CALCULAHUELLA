from __future__ import annotations


BILLING_CYCLES_PER_YEAR = {
    "Mensual": 12,
    "Anual": 1,
}


def billing_cycles_per_year(billing_cycle: str) -> int:
    """Return how many recurring charges belong to the first contract year."""
    try:
        return BILLING_CYCLES_PER_YEAR[billing_cycle]
    except KeyError as exc:
        raise ValueError("Ciclo de facturación inválido") from exc


def recurring_first_year_value(recurring_fee: float, billing_cycle: str) -> float:
    """Annualize the negotiated recurring charge without changing its cycle meaning."""
    return round(recurring_fee * billing_cycles_per_year(billing_cycle), 2)


def proposal_first_year_total(
    implementation_fee: float,
    recurring_fee: float,
    discount_amount: float,
    tax_rate: float,
    billing_cycle: str,
) -> float:
    """Contract value for year one: implementation + all cycles - one-time discount + tax."""
    subtotal = implementation_fee + recurring_first_year_value(recurring_fee, billing_cycle) - discount_amount
    return round(subtotal * (1 + tax_rate / 100), 2)


def proposal_initial_payment(
    implementation_fee: float,
    recurring_fee: float,
    discount_amount: float,
    tax_rate: float,
) -> float:
    """Activation charge: implementation + the first recurring cycle - one-time discount + tax."""
    subtotal = implementation_fee + recurring_fee - discount_amount
    return round(subtotal * (1 + tax_rate / 100), 2)


def subscription_custom_monthly_fee(recurring_fee: float, billing_cycle: str) -> float:
    """Persist the negotiated recurring price using the subscription model's monthly-equivalent field."""
    cycles = billing_cycles_per_year(billing_cycle)
    return round(recurring_fee if cycles == 12 else recurring_fee / 12, 2)
