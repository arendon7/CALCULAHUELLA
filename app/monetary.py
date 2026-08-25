from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")
NORMALIZED_MONEY_QUANTUM = Decimal("0.000001")
RATE_QUANTUM = Decimal("0.0001")
HUNDRED = Decimal("100")

# V2.60.9 portable-capacity contract.
#
# PostgreSQL NUMERIC can represent substantially larger exact values than
# SQLite's numeric path. SQLAlchemy may use an IEEE-754 double intermediary for
# SQLite Numeric binds, so the portable limits stay below the magnitude where
# one ULP can exceed the target quantum. This guarantees that every accepted
# value preserves its economic scale on both supported database engines.
#
# For cents, all magnitudes below 2**46 have binary spacing < 0.01.
# For six decimals, all magnitudes below 2**33 have spacing < 0.000001.
# The rate's physical NUMERIC(9,4) range is already far below its float-risk
# threshold; business input remains capped at 100% by parse_nonnegative_rate.
MONEY_PORTABLE_MAX = Decimal(2**46) - MONEY_QUANTUM
NORMALIZED_MONEY_PORTABLE_MAX = Decimal(2**33) - NORMALIZED_MONEY_QUANTUM
RATE_STORAGE_MAX = Decimal("99999.9999")


def decimal_from_value(raw: object, label: str = "el valor") -> Decimal:
    """Convert user/ORM input without importing a binary float representation.

    ``str`` is intentional for legacy floats: it recovers their human decimal
    value instead of materializing the IEEE-754 expansion through
    ``Decimal.from_float``.
    """

    value_raw = str(raw if raw is not None else "").strip()
    if not value_raw:
        raise ValueError(f"Define {label}.")
    try:
        value = Decimal(value_raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label.capitalize()} debe ser un número válido.") from exc
    if not value.is_finite():
        raise ValueError(f"{label.capitalize()} debe ser un número finito.")
    return value


def quantize_money(raw: object) -> Decimal:
    return decimal_from_value(raw).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_normalized_money(raw: object) -> Decimal:
    return decimal_from_value(raw).quantize(NORMALIZED_MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_rate(raw: object) -> Decimal:
    return decimal_from_value(raw).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def _parse_nonnegative_decimal(
    raw: object,
    label: str,
    *,
    quantum: Decimal,
    maximum: Decimal | None = None,
) -> Decimal:
    value = decimal_from_value(raw, label)
    if value < 0:
        raise ValueError(f"{label.capitalize()} no puede ser negativo.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label.capitalize()} no puede ser mayor que {maximum:f}.")
    try:
        return value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"{label.capitalize()} excede la capacidad numérica permitida.") from exc


def parse_nonnegative_money(
    raw: object,
    label: str,
    *,
    maximum: Decimal = MONEY_PORTABLE_MAX,
) -> Decimal:
    return _parse_nonnegative_decimal(raw, label, quantum=MONEY_QUANTUM, maximum=maximum)


def parse_nonnegative_normalized_money(
    raw: object,
    label: str,
    *,
    maximum: Decimal = NORMALIZED_MONEY_PORTABLE_MAX,
) -> Decimal:
    return _parse_nonnegative_decimal(raw, label, quantum=NORMALIZED_MONEY_QUANTUM, maximum=maximum)


def parse_nonnegative_rate(raw: object, label: str, *, maximum: Decimal = HUNDRED) -> Decimal:
    return _parse_nonnegative_decimal(raw, label, quantum=RATE_QUANTUM, maximum=min(maximum, RATE_STORAGE_MAX))


def money_tax(base: object, tax_rate: object) -> Decimal:
    base_amount = quantize_money(base)
    rate = quantize_rate(tax_rate)
    return (base_amount * rate / HUNDRED).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
