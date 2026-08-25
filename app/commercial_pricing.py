from __future__ import annotations

from decimal import Decimal

from .money import ONE_HUNDRED, TWELVE, as_decimal, quantize_money, quantize_recurring_basis


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


def _decimal(value: object, label: str) -> Decimal:
    return value if isinstance(value, Decimal) else as_decimal(value, label)


def recurring_first_year_value(recurring_fee: object, billing_cycle: str) -> Decimal:
    """Annualize the negotiated recurring charge and settle the derived year value to cents."""
    recurring = _decimal(recurring_fee, "el valor recurrente")
    return quantize_money(recurring * billing_cycles_per_year(billing_cycle))


def proposal_first_year_total(
    implementation_fee: object,
    recurring_fee: object,
    discount_amount: object,
    tax_rate: object,
    billing_cycle: str,
) -> Decimal:
    """Contract value for year one: implementation + all cycles - one-time discount + tax."""
    implementation = _decimal(implementation_fee, "la implementación")
    discount = _decimal(discount_amount, "el descuento")
    rate = _decimal(tax_rate, "la tasa de impuesto")
    subtotal = implementation + recurring_first_year_value(recurring_fee, billing_cycle) - discount
    return quantize_money(subtotal * (Decimal("1") + rate / ONE_HUNDRED))


def proposal_initial_payment(
    implementation_fee: object,
    recurring_fee: object,
    discount_amount: object,
    tax_rate: object,
) -> Decimal:
    """Activation charge: implementation + first recurring cycle - one-time discount + tax."""
    implementation = _decimal(implementation_fee, "la implementación")
    recurring = _decimal(recurring_fee, "el valor recurrente")
    discount = _decimal(discount_amount, "el descuento")
    rate = _decimal(tax_rate, "la tasa de impuesto")
    subtotal = implementation + recurring - discount
    return quantize_money(subtotal * (Decimal("1") + rate / ONE_HUNDRED))


def subscription_custom_monthly_fee(recurring_fee: object, billing_cycle: str) -> Decimal:
    """Persist the negotiated recurring price as a six-decimal monthly-equivalent basis."""
    recurring = _decimal(recurring_fee, "el valor recurrente")
    cycles = billing_cycles_per_year(billing_cycle)
    monthly_basis = recurring if cycles == 12 else recurring / TWELVE
    return quantize_recurring_basis(monthly_basis)
