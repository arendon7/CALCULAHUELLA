from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Final


MONEY_PRECISION: Final = 18
MONEY_SCALE: Final = 2
RATE_PRECISION: Final = 9
RATE_SCALE: Final = 6
RECURRING_BASIS_PRECISION: Final = 18
RECURRING_BASIS_SCALE: Final = 6

MONEY_QUANTUM: Final = Decimal("0.01")
RATE_QUANTUM: Final = Decimal("0.000001")
RECURRING_BASIS_QUANTUM: Final = Decimal("0.000001")
ZERO: Final = Decimal("0")
ONE_HUNDRED: Final = Decimal("100")
TWELVE: Final = Decimal("12")


def as_decimal(raw: object, label: str) -> Decimal:
    """Parse a finite decimal value without routing through binary float arithmetic."""
    value_raw = str(raw if raw is not None else "").strip()
    if not value_raw:
        raise ValueError(f"Define {label}.")
    try:
        value = Decimal(value_raw)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label.capitalize()} debe ser un número válido.") from exc
    if not value.is_finite():
        raise ValueError(f"{label.capitalize()} debe ser un número finito.")
    return value


def _fractional_digits(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return max(0, -int(exponent))


def parse_nonnegative_decimal(
    raw: object,
    label: str,
    *,
    maximum: Decimal | None = None,
    scale: int | None = None,
) -> Decimal:
    value = as_decimal(raw, label)
    if value < ZERO:
        raise ValueError(f"{label.capitalize()} no puede ser negativo.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label.capitalize()} no puede ser mayor que {maximum:g}.")
    if scale is not None and _fractional_digits(value) > scale:
        suffix = "decimal" if scale == 1 else "decimales"
        raise ValueError(f"{label.capitalize()} admite máximo {scale} {suffix}.")
    return value


def parse_money(raw: object, label: str) -> Decimal:
    """Parse an authoritative monetary input; user-entered money is never silently rounded."""
    return parse_nonnegative_decimal(raw, label, scale=MONEY_SCALE)


def parse_rate(raw: object, label: str) -> Decimal:
    """Parse a percentage rate with explicit precision and the existing 0..100 business bound."""
    return parse_nonnegative_decimal(raw, label, maximum=ONE_HUNDRED, scale=RATE_SCALE)


def quantize_money(value: object) -> Decimal:
    """Round a derived monetary result to the settlement precision."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite():
        raise ValueError("El valor monetario derivado debe ser finito.")
    return decimal_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_rate(value: object) -> Decimal:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite():
        raise ValueError("La tasa derivada debe ser finita.")
    return decimal_value.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_recurring_basis(value: object) -> Decimal:
    """Keep sub-cent monthly-equivalent precision so annual values are not rounded prematurely."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite():
        raise ValueError("La base recurrente derivada debe ser finita.")
    return decimal_value.quantize(RECURRING_BASIS_QUANTUM, rounding=ROUND_HALF_UP)


def money_equal(left: object, right: object) -> bool:
    """Compare economic values at the authoritative settlement precision."""
    return quantize_money(left) == quantize_money(right)
