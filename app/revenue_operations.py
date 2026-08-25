from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from .monetary import (
    HUNDRED,
    MONEY_PORTABLE_MAX,
    money_tax,
    parse_nonnegative_money,
    parse_nonnegative_rate,
    quantize_money,
    quantize_rate,
)


CONTRACT_SIGNATURE_VERSION = "1.1"
INVOICE_TOTAL_WITH_TAX = "total_with_tax"
INVOICE_BASE_BEFORE_TAX = "base_before_tax"
INVOICE_LEGACY_UNKNOWN = "legacy_unknown"


class ParsedDecimal(Decimal):
    """Decimal form value retaining the legacy ``is_integer`` convenience API."""

    def is_integer(self) -> bool:
        return self == self.to_integral_value()


def canonical_utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def canonical_utc_timestamp(value: datetime) -> str:
    return canonical_utc_datetime(value).isoformat()


def parse_nonnegative_number(
    raw: object,
    label: str,
    *,
    maximum: float | Decimal | None = MONEY_PORTABLE_MAX,
) -> ParsedDecimal:
    """Parse a generic nonnegative Revenue Operations form number exactly.

    Monetary values should use ``parse_nonnegative_money`` when the form can
    distinguish them, because that helper also applies the two-decimal policy.
    This compatibility helper is shared by mixed operational forms (currently
    contract value + notice days), so it remains unquantized but V2.60.9 caps
    it at the portable economic ceiling by default. Callers with a tighter
    non-monetary domain may continue to pass an explicit ``maximum``.
    """

    value_raw = str(raw if raw is not None else "").strip()
    if not value_raw:
        raise ValueError(f"Define {label}.")
    try:
        value = ParsedDecimal(value_raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label.capitalize()} debe ser un número válido.") from exc
    if not value.is_finite():
        raise ValueError(f"{label.capitalize()} debe ser un número finito.")
    if value < 0:
        raise ValueError(f"{label.capitalize()} no puede ser negativo.")
    if maximum is not None:
        maximum_decimal = Decimal(str(maximum))
        if value > maximum_decimal:
            raise ValueError(f"{label.capitalize()} no puede ser mayor que {maximum_decimal:f}.")
    return value


def validate_date_window(start: date, end: date | None, *, label: str) -> None:
    if end is not None and end < start:
        raise ValueError(f"La fecha final de {label} no puede ser anterior a la fecha inicial.")


def contract_signature_payload(contract, signed_by: str, signed_email: str, signed_at: datetime) -> dict[str, object]:
    """Return the complete contractual signature snapshot.

    V2.60.7 preserves the V2.60.6 signature version and canonical two-decimal
    contract-value representation. Existing signature payloads/hashes are never
    rewritten by the precision migration.
    """

    return {
        "signature_version": CONTRACT_SIGNATURE_VERSION,
        "reference": contract.reference,
        "organization_id": contract.organization_id,
        "proposal_id": contract.proposal_id,
        "parent_contract_id": contract.parent_contract_id,
        "title": contract.title,
        "contract_version": contract.version,
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat() if contract.end_date else "",
        "renewal_type": contract.renewal_type,
        "auto_renew": bool(contract.auto_renew),
        "notice_days": int(contract.notice_days),
        "contract_value": f"{quantize_money(contract.contract_value):.2f}",
        "billing_cycle": contract.billing_cycle,
        "owner": contract.owner,
        "terms_snapshot": contract.terms_snapshot,
        "signed_by": signed_by.strip(),
        "signed_email": signed_email.strip().lower(),
        "signed_at": canonical_utc_timestamp(signed_at),
    }


def contract_signature_source(contract, signed_by: str, signed_email: str, signed_at: datetime) -> str:
    return json.dumps(
        contract_signature_payload(contract, signed_by, signed_email, signed_at),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def contract_signature_hash(contract, signed_by: str, signed_email: str, signed_at: datetime) -> str:
    source = contract_signature_source(contract, signed_by, signed_email, signed_at)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def activation_breakdown(
    implementation_fee: object,
    recurring_fee: object,
    discount_amount: object,
    tax_rate: object,
) -> dict[str, Decimal]:
    """Return the exact V2.60.6 activation semantics using decimal arithmetic."""

    implementation = quantize_money(implementation_fee)
    recurring = quantize_money(recurring_fee)
    discount = quantize_money(discount_amount)
    rate = quantize_rate(tax_rate)
    net = quantize_money(implementation + recurring - discount)
    tax = money_tax(net, rate)
    return {
        "net_amount": net,
        "tax_rate_snapshot": rate,
        "tax_amount": tax,
        "total_amount": quantize_money(net + tax),
    }


__all__ = [
    "CONTRACT_SIGNATURE_VERSION",
    "HUNDRED",
    "INVOICE_BASE_BEFORE_TAX",
    "INVOICE_LEGACY_UNKNOWN",
    "INVOICE_TOTAL_WITH_TAX",
    "ParsedDecimal",
    "activation_breakdown",
    "canonical_utc_datetime",
    "canonical_utc_timestamp",
    "contract_signature_hash",
    "contract_signature_payload",
    "contract_signature_source",
    "parse_nonnegative_money",
    "parse_nonnegative_number",
    "parse_nonnegative_rate",
    "validate_date_window",
]
