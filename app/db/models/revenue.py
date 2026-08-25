from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from sqlalchemy import DateTime, Numeric, String, Text, select
from sqlalchemy.orm import mapped_column

from ...monetary import MONEY_PORTABLE_MAX, NORMALIZED_MONEY_PORTABLE_MAX, RATE_STORAGE_MAX
from ..base import Base
from .commercial import (
    BillingInvoice,
    CommercialProposal,
    OrganizationSubscription,
    PaymentTransaction,
    RenewalOpportunity,
    ServiceContract,
    ServicePlan,
)


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
    """Decimal compatible with historical arithmetic that used float literals.

    V2.60.7 never converts a float through its binary representation. If old
    application/bootstrap code combines a persisted monetary value with a
    literal such as ``1.19``, the literal is first converted through ``str`` and
    every arithmetic result remains an ``ExactDecimal`` until an explicit
    monetary quantization boundary is reached.
    """

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
    """NUMERIC with deterministic scale and portable capacity enforcement.

    PostgreSQL enforces NUMERIC precision physically while SQLite commonly uses
    an IEEE-754 intermediary for Numeric binds. V2.60.9 validates both the SQL
    storage range and a conservative portable range before either driver sees
    the value, then verifies that a float round trip would preserve the target
    economic quantum. The result is one fail-closed contract for both engines.
    """

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

    def bind_processor(self, dialect):
        parent = super().bind_processor(dialect)
        precision, scale, quantum, physical_maximum, portable_maximum, overflow_threshold = self._storage_contract()

        def process(value):
            if value is None:
                return None
            try:
                exact = value if isinstance(value, Decimal) else Decimal(str(value))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError("El valor económico persistido debe ser un número válido") from exc
            if not exact.is_finite():
                raise ValueError("Los valores monetarios persistidos deben ser finitos")
            if abs(exact) >= overflow_threshold:
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
            if abs(quantized) > physical_maximum or abs(quantized) > portable_maximum:
                raise ValueError(
                    f"El valor económico excede el límite portable de NUMERIC({precision},{scale}): "
                    f"{portable_maximum}"
                )

            # Guard the worst supported persistence path explicitly. Converting
            # through str(float(...)) does not become the stored representation;
            # it only proves that a driver using a double intermediary cannot
            # change the value at the declared economic scale.
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


def _money_type() -> Numeric:
    return ExactNumeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)


def _normalized_money_type() -> Numeric:
    return ExactNumeric(MONEY_PRECISION, NORMALIZED_MONEY_SCALE, asdecimal=True)


def _rate_type() -> Numeric:
    return ExactNumeric(RATE_PRECISION, RATE_SCALE, asdecimal=True)


def _set_exact_type(model, column_name: str, column_type: Numeric) -> None:
    """Bind an existing commercial authority to its exact numeric type.

    Scientific, environmental, usage and customer-success measurements keep
    their Float semantics in the owning model modules. V2.60.8 guarantees
    deterministic rounding and V2.60.9 additionally makes numeric capacity and
    scale preservation fail closed across SQLite and PostgreSQL.
    """

    model.__table__.c[column_name].type = column_type


# Existing commercial authorities. The monthly-equivalent subscription value
# needs six decimals so an annual negotiated amount survives /12 then *12 and
# is rounded only when it becomes a payable monetary amount.
for _model, _column in (
    (ServicePlan, "monthly_fee"),
    (ServicePlan, "annual_fee"),
    (BillingInvoice, "amount"),
    (CommercialProposal, "implementation_fee"),
    (CommercialProposal, "recurring_fee"),
    (CommercialProposal, "discount_amount"),
    (CommercialProposal, "first_year_total"),
    (PaymentTransaction, "amount"),
    (ServiceContract, "contract_value"),
    (RenewalOpportunity, "forecast_amount"),
):
    _set_exact_type(_model, _column, _money_type())

_set_exact_type(OrganizationSubscription, "custom_monthly_fee", _normalized_money_type())
_set_exact_type(CommercialProposal, "tax_rate", _rate_type())


# V2.60.6 extends the existing authorities instead of creating one-to-one tables.
# Nullable columns are deliberate: historical rows remain unknown until there is
# evidence to classify them. V2.60.7 changes representation, not semantics.
BillingInvoice.charge_type = mapped_column(String(40), nullable=True)
BillingInvoice.amount_semantics = mapped_column(String(40), nullable=True)
BillingInvoice.net_amount = mapped_column(_money_type(), nullable=True)
BillingInvoice.tax_rate_snapshot = mapped_column(_rate_type(), nullable=True)
BillingInvoice.tax_amount = mapped_column(_money_type(), nullable=True)
BillingInvoice.total_amount = mapped_column(_money_type(), nullable=True)
BillingInvoice.source_reference = mapped_column(String(120), nullable=True)
BillingInvoice.classification_note = mapped_column(Text, nullable=True)
BillingInvoice.semantics_created_at = mapped_column(DateTime, nullable=True)

ServiceContract.signature_version = mapped_column(String(20), nullable=True)
ServiceContract.signature_payload = mapped_column(Text, nullable=True)
ServiceContract.signature_snapshot_created_at = mapped_column(DateTime, nullable=True)


# Read-only compatibility projections preserve the semantic language used by
# Revenue Operations tests and query code without adding physical ORM tables.
_billing_projection = (
    select(
        BillingInvoice.id.label("invoice_id"),
        BillingInvoice.charge_type,
        BillingInvoice.amount_semantics,
        BillingInvoice.net_amount,
        BillingInvoice.tax_rate_snapshot,
        BillingInvoice.tax_amount,
        BillingInvoice.total_amount,
        BillingInvoice.source_reference,
        BillingInvoice.classification_note,
        BillingInvoice.semantics_created_at.label("created_at"),
    )
    .where(BillingInvoice.amount_semantics.is_not(None))
    .subquery("billing_charge_breakdown_projection")
)


class BillingChargeBreakdown(Base):
    """Read-only semantic projection over ``billing_invoices``.

    The write authority is ``BillingInvoice`` itself. Rows without
    ``amount_semantics`` are intentionally absent and therefore remain legacy
    unknown rather than being auto-classified.
    """

    __table__ = _billing_projection
    __mapper_args__ = {"primary_key": [_billing_projection.c.invoice_id]}


_contract_signature_projection = (
    select(
        ServiceContract.id.label("contract_id"),
        ServiceContract.signature_version,
        ServiceContract.signature_payload.label("canonical_payload"),
        ServiceContract.signature_hash.label("payload_hash"),
        ServiceContract.signature_snapshot_created_at.label("created_at"),
    )
    .where(ServiceContract.signature_version.is_not(None))
    .subquery("contract_signature_snapshot_projection")
)


class ContractSignatureSnapshot(Base):
    """Read-only canonical-signature projection over ``service_contracts``."""

    __table__ = _contract_signature_projection
    __mapper_args__ = {"primary_key": [_contract_signature_projection.c.contract_id]}
