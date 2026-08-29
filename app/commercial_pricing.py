from __future__ import annotations

from decimal import Decimal

from .monetary import money_tax, quantize_money, quantize_normalized_money, quantize_rate


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


def recurring_first_year_value(recurring_fee: object, billing_cycle: str) -> Decimal:
    """Annualize the negotiated recurring charge without changing its cycle meaning."""
    recurring = quantize_money(recurring_fee)
    return quantize_money(recurring * billing_cycles_per_year(billing_cycle))


def proposal_first_year_total(
    implementation_fee: object,
    recurring_fee: object,
    discount_amount: object,
    tax_rate: object,
    billing_cycle: str,
) -> Decimal:
    """Contract value for year one: implementation + all cycles - one-time discount + tax."""
    implementation = quantize_money(implementation_fee)
    recurring_year = recurring_first_year_value(recurring_fee, billing_cycle)
    discount = quantize_money(discount_amount)
    rate = quantize_rate(tax_rate)
    subtotal = quantize_money(implementation + recurring_year - discount)
    return quantize_money(subtotal + money_tax(subtotal, rate))


def proposal_initial_payment(
    implementation_fee: object,
    recurring_fee: object,
    discount_amount: object,
    tax_rate: object,
) -> Decimal:
    """Activation charge: implementation + the first recurring cycle - one-time discount + tax."""
    implementation = quantize_money(implementation_fee)
    recurring = quantize_money(recurring_fee)
    discount = quantize_money(discount_amount)
    rate = quantize_rate(tax_rate)
    subtotal = quantize_money(implementation + recurring - discount)
    return quantize_money(subtotal + money_tax(subtotal, rate))


def subscription_custom_monthly_fee(recurring_fee: object, billing_cycle: str) -> Decimal:
    """Persist the negotiated recurring price using the historical monthly-equivalent field.

    The six-decimal internal representation is deliberate. For annual contracts
    the application has always stored ``recurring_fee / 12`` and reconstructed
    the annual base with ``* 12``. Keeping six decimals prevents a two-cent
    storage policy from changing the established annual economics.
    """

    recurring = quantize_money(recurring_fee)
    cycles = billing_cycles_per_year(billing_cycle)
    monthly_equivalent = recurring if cycles == 12 else recurring / Decimal("12")
    return quantize_normalized_money(monthly_equivalent)
