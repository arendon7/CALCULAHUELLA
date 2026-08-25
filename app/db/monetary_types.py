from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from sqlalchemy import Numeric

from ..monetary import MONEY_PORTABLE_MAX, NORMALIZED_MONEY_PORTABLE_MAX, RATE_STORAGE_MAX


MONEY_PRECISION = 20
MONEY_SCALE = 2
NORMALIZED_MONEY_SCALE = 6
RATE_PRECISION = 9
RATE_SCALE = 4

_PORTABLE_MAX_BY_NUMERIC = {
    (MONEY_PRECISION, MONEY_SCALE): MONEY_PORTABLE_MAX,
    (MONEY_PRECISION, NORMALIZED_MONEY_SCALE): NORMALIZED_MONEY_PORTABLE_MAX,
    (RATE_PRECISION, RATE_SCALE): RATE_STORAGE_MAX,
}


class ExactDecimal(Decimal):
    """Decimal compatible with historical arithmetic that used float literals."""

    @staticmethod
    def _coerce(other: object) -> object:
        return Decimal(str(other)) if isinstance(other, float) else other

    @classmethod
    def _wrap(cls, value: object) -> object:
        if value is NotImplemented:
            return value
        if isinstance(value, Decimal) and not isinstance(value, cls):
            return cls(value)
        return value

    def __add__(self, other: object):
        return self._wrap(super().__add__(self._coerce(other)))

    def __radd__(self, other: object):
        return self._wrap(super().__radd__(self._coerce(other)))

    def __sub__(self, other: object):
        return self._wrap(super().__sub__(self._coerce(other)))

    def __rsub__(self, other: object):
        return self._wrap(super().__rsub__(self._coerce(other)))

    def __mul__(self, other: object):
        return self._wrap(super().__mul__(self._coerce(other)))

    def __rmul__(self, other: object):
        return self._wrap(super().__rmul__(self._coerce(other)))

    def __truediv__(self, other: object):
        return self._wrap(super().__truediv__(self._coerce(other)))

    def __rtruediv__(self, other: object):
        return self._wrap(super().__rtruediv__(self._coerce(other)))


class ExactNumeric(Numeric):
    """NUMERIC with deterministic scale and portable capacity enforcement."""

    def _storage_contract(self) -> tuple[int, int, Decimal, Decimal, Decimal, Decimal]:
        precision = int(self.precision or 0)
        scale = int(self.scale or 0)
        if precision <= 0 or scale < 0 or scale > precision:
            raise ValueError("La precisión NUMERIC configurada no es válida")
        quantum = Decimal("1").scaleb(-scale)
        physical_maximum = (Decimal(10) ** (precision - scale)) - quantum
        portable_maximum = min(
            physical_maximum,
            _PORTABLE_MAX_BY_NUMERIC.get((precision, scale), physical_maximum),
        )
        overflow_threshold = portable_maximum + (quantum / Decimal(2))
        return precision, scale, quantum, physical_maximum, portable_maximum, overflow_threshold

    def normalize_value(self, value: object) -> Decimal | None:
        if value is None:
            return None
        precision, scale, quantum, physical_maximum, portable_maximum, overflow_threshold = self._storage_contract()
        try:
            exact = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("El valor económico persistido debe ser un número válido") from exc
        if not exact.is_finite():
            raise ValueError("Los valores monetarios persistidos deben ser finitos")
        if exact.copy_abs() >= overflow_threshold:
            raise ValueError(
                f"El valor económico excede el límite portable de NUMERIC({precision},{scale}): "
                f"{portable_maximum}"
            )
        try:
            with localcontext() as context:
                context.prec = max(precision + 2, 28)
                quantized = exact.quantize(quantum, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise ValueError(
                f"El valor económico no puede representarse como NUMERIC({precision},{scale})"
            ) from exc
        quantized_magnitude = quantized.copy_abs()
        if quantized_magnitude > physical_maximum or quantized_magnitude > portable_maximum:
            raise ValueError(
                f"El valor económico excede el límite portable de NUMERIC({precision},{scale}): "
                f"{portable_maximum}"
            )

        try:
            portable_float = float(quantized)
            portable_decimal = Decimal(str(portable_float))
            with localcontext() as context:
                context.prec = max(precision + 2, 28)
                portable_roundtrip = portable_decimal.quantize(quantum, rounding=ROUND_HALF_UP)
        except (InvalidOperation, OverflowError, ValueError) as exc:
            raise ValueError(
                f"El valor económico no conserva su escala NUMERIC({precision},{scale}) "
                "en el contrato portable de persistencia"
            ) from exc
        if portable_roundtrip != quantized:
            raise ValueError(
                f"El valor económico no conserva su escala NUMERIC({precision},{scale}) "
                "en el contrato portable de persistencia"
            )
        return quantized

    def bind_processor(self, dialect):
        parent = super().bind_processor(dialect)

        def process(value):
            quantized = self.normalize_value(value)
            if quantized is None:
                return None
            return parent(quantized) if parent is not None else quantized

        return process

    def result_processor(self, dialect, coltype):
        parent = super().result_processor(dialect, coltype)

        def process(value):
            converted = parent(value) if parent is not None else value
            if converted is None or isinstance(converted, ExactDecimal):
                return converted
            return ExactDecimal(str(converted))

        return process


def money_type() -> ExactNumeric:
    return ExactNumeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)


def normalized_money_type() -> ExactNumeric:
    return ExactNumeric(MONEY_PRECISION, NORMALIZED_MONEY_SCALE, asdecimal=True)


def rate_type() -> ExactNumeric:
    return ExactNumeric(RATE_PRECISION, RATE_SCALE, asdecimal=True)


__all__ = [
    "ExactDecimal",
    "ExactNumeric",
    "MONEY_PRECISION",
    "MONEY_SCALE",
    "NORMALIZED_MONEY_SCALE",
    "RATE_PRECISION",
    "RATE_SCALE",
    "money_type",
    "normalized_money_type",
    "rate_type",
]
