from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Mapping

from .revenue_operations import INVOICE_BASE_BEFORE_TAX, INVOICE_TOTAL_WITH_TAX


_PRIORITY_LABELS = {
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Próxima",
}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


@dataclass(frozen=True, slots=True)
class RevenueAction:
    """Read-only next action derived from persisted commercial facts.

    V2.60.11 deliberately keeps this projection outside the database. It does
    not score customers, mutate lifecycle state, infer taxes, or manufacture a
    due date. ``due_date`` is only populated when the source record already has
    a meaningful persisted date.
    """

    key: str
    priority: str
    priority_label: str
    category: str
    title: str
    subject: str
    detail: str
    href: str
    due_date: date | None = None
    amount: Decimal | None = None
    amount_label: str = ""


def _organization_label(organization_names: Mapping[int, str], organization_id: int | None) -> str:
    if organization_id is None:
        return "Organización"
    return organization_names.get(organization_id) or "Organización"


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _action(
    *,
    key: str,
    priority: str,
    category: str,
    title: str,
    subject: str,
    detail: str,
    href: str,
    due_date: date | None = None,
    amount: object = None,
    amount_label: str = "",
) -> RevenueAction:
    if priority not in _PRIORITY_ORDER:
        raise ValueError(f"Prioridad de Revenue Action no soportada: {priority}")
    return RevenueAction(
        key=key,
        priority=priority,
        priority_label=_PRIORITY_LABELS[priority],
        category=category,
        title=title,
        subject=subject,
        detail=detail,
        href=href,
        due_date=due_date,
        amount=_decimal_or_none(amount),
        amount_label=amount_label,
    )


def _collection_due_key(item: Any) -> tuple[bool, date, int]:
    due_at = getattr(item, "due_at", None)
    return (due_at is None, due_at or date.max, int(getattr(item, "id", 0) or 0))


def build_revenue_action_queue(
    *,
    contracts: Iterable[Any],
    orders: Iterable[Any],
    invoices: Iterable[Any],
    proposals: Iterable[Any],
    collection_actions: Iterable[Any],
    breakdown_by_invoice: Mapping[int, Any],
    organization_names: Mapping[int, str],
    today: date,
) -> list[RevenueAction]:
    """Build a deterministic action queue without changing authoritative data.

    Priority is rule-based and explainable:
    - critical: a persisted deadline is already breached;
    - high: an explicit commercial handoff is blocked or due now;
    - medium: a known next milestone is approaching.

    The projection intentionally does not create a generic risk score. Every
    item names the source condition in human language and links back to the
    authoritative operational surface where the user can act.
    """

    contract_items = list(contracts)
    order_items = list(orders)
    invoice_items = list(invoices)
    proposal_items = list(proposals)
    collection_items = list(collection_actions)
    result: list[RevenueAction] = []

    contracted_proposal_ids = {
        int(item.proposal_id)
        for item in contract_items
        if getattr(item, "proposal_id", None) is not None
    }

    # Accepted proposal -> contract is the first post-sale handoff. Do not
    # duplicate it once any contract is already linked to that proposal.
    for proposal in proposal_items:
        if (
            getattr(proposal, "status", None) == "Aceptada"
            and getattr(proposal, "organization_id", None) is not None
            and int(getattr(proposal, "id")) not in contracted_proposal_ids
        ):
            result.append(_action(
                key=f"proposal:{proposal.id}:contract",
                priority="high",
                category="Formalización",
                title="Formalizar propuesta aceptada",
                subject=f"{proposal.reference} · {proposal.company_name}",
                detail="La propuesta está aceptada y tiene organización asociada, pero todavía no existe un contrato vinculado.",
                href="#contratos",
            ))

    for contract in contract_items:
        organization = _organization_label(organization_names, getattr(contract, "organization_id", None))
        subject = f"{contract.reference} · {organization}"
        status = getattr(contract, "status", "")
        end_date = getattr(contract, "end_date", None)

        if status == "Borrador" and not getattr(contract, "signature_hash", ""):
            result.append(_action(
                key=f"contract:{contract.id}:signature",
                priority="high",
                category="Contrato",
                title="Completar firma contractual",
                subject=subject,
                detail="El contrato permanece en borrador y no tiene firma registrada ni snapshot contractual.",
                href="#contratos",
            ))

        if status != "Vigente" or end_date is None:
            continue

        days_to_end = (end_date - today).days
        notice_days = max(0, int(getattr(contract, "notice_days", 0) or 0))
        renewal_type = getattr(contract, "renewal_type", "")
        nonrenewable = renewal_type == "No renovable"

        if days_to_end < 0:
            result.append(_action(
                key=f"contract:{contract.id}:expired-status",
                priority="critical",
                category="Contrato",
                title="Resolver vigencia contractual vencida",
                subject=subject,
                detail="El contrato figura como Vigente aunque su fecha final ya pasó; requiere cierre, corrección de estado o formalización de continuidad.",
                href="#contratos",
                due_date=end_date,
            ))
        elif days_to_end <= notice_days:
            result.append(_action(
                key=f"contract:{contract.id}:notice-window",
                priority="high",
                category="Renovación" if not nonrenewable else "Cierre contractual",
                title="Abrir decisión de renovación" if not nonrenewable else "Preparar cierre contractual",
                subject=subject,
                detail=(
                    f"Está dentro de su ventana de preaviso de {notice_days} días."
                    if not nonrenewable
                    else f"Es no renovable y está dentro de su ventana de cierre de {notice_days} días."
                ),
                href="#contratos",
                due_date=end_date,
            ))
        elif days_to_end <= 120:
            result.append(_action(
                key=f"contract:{contract.id}:upcoming-end",
                priority="medium",
                category="Renovación" if not nonrenewable else "Cierre contractual",
                title="Preparar renovación" if not nonrenewable else "Preparar cierre contractual",
                subject=subject,
                detail=(
                    f"Vence en {days_to_end} días; la ventana de preaviso registrada es de {notice_days} días."
                    if not nonrenewable
                    else f"Vence en {days_to_end} días y está marcado como no renovable."
                ),
                href="#contratos",
                due_date=end_date,
            ))

    for order in order_items:
        organization = _organization_label(organization_names, getattr(order, "organization_id", None))
        subject = f"{order.reference} · {organization}"
        status = getattr(order, "status", "")
        planned_start = getattr(order, "planned_start", None)
        planned_end = getattr(order, "planned_end", None)

        if status == "Bloqueada":
            result.append(_action(
                key=f"order:{order.id}:blocked",
                priority="high",
                category="Servicio",
                title="Desbloquear orden de servicio",
                subject=subject,
                detail="La ejecución está explícitamente marcada como Bloqueada; revisa notas, responsable y próximo compromiso.",
                href="#ordenes",
                due_date=planned_end or planned_start,
            ))
        elif status == "Entregada":
            result.append(_action(
                key=f"order:{order.id}:acceptance",
                priority="medium",
                category="Servicio",
                title="Cerrar aceptación de entrega",
                subject=subject,
                detail="La orden ya fue entregada pero todavía no figura como Aceptada.",
                href="#ordenes",
                due_date=planned_end,
            ))
        elif status == "Planeada" and planned_start is not None and planned_start < today:
            result.append(_action(
                key=f"order:{order.id}:late-start",
                priority="high",
                category="Servicio",
                title="Iniciar o reprogramar orden atrasada",
                subject=subject,
                detail="La fecha prevista de inicio ya pasó y la orden continúa en estado Planeada.",
                href="#ordenes",
                due_date=planned_start,
            ))
        elif status == "En ejecución" and planned_end is not None and planned_end < today:
            result.append(_action(
                key=f"order:{order.id}:late-end",
                priority="high",
                category="Servicio",
                title="Cerrar o reprogramar ejecución vencida",
                subject=subject,
                detail="La fecha prevista de finalización ya pasó y la orden continúa En ejecución.",
                href="#ordenes",
                due_date=planned_end,
            ))

    pending_collection_by_invoice: dict[int, Any] = {}
    for collection in collection_items:
        if getattr(collection, "status", None) != "Pendiente":
            continue
        invoice_id = getattr(collection, "invoice_id", None)
        if invoice_id is None:
            continue
        current = pending_collection_by_invoice.get(int(invoice_id))
        if current is None or _collection_due_key(collection) < _collection_due_key(current):
            pending_collection_by_invoice[int(invoice_id)] = collection

    represented_collection_ids: set[int] = set()
    for invoice in invoice_items:
        if getattr(invoice, "status", None) not in {"Pendiente", "Vencida"}:
            continue

        invoice_id = int(invoice.id)
        organization = _organization_label(organization_names, getattr(invoice, "organization_id", None))
        subject = f"{invoice.reference} · {organization}"
        due_date = getattr(invoice, "due_date", None)
        overdue = due_date is not None and due_date < today
        days_to_due = (due_date - today).days if due_date is not None else None
        breakdown = breakdown_by_invoice.get(invoice_id)
        semantics = (
            getattr(breakdown, "amount_semantics", None)
            if breakdown is not None
            else getattr(invoice, "amount_semantics", None)
        )
        collection = pending_collection_by_invoice.get(invoice_id)

        if semantics == INVOICE_TOTAL_WITH_TAX:
            amount = getattr(breakdown, "total_amount", None) if breakdown is not None else getattr(invoice, "total_amount", None)
            amount_label = "Total conocido"
        elif semantics == INVOICE_BASE_BEFORE_TAX:
            amount = getattr(breakdown, "net_amount", None) if breakdown is not None else getattr(invoice, "net_amount", None)
            amount_label = "Base antes de impuesto"
        else:
            amount = getattr(invoice, "amount", None)
            amount_label = "Importe legacy sin clasificar"

        if overdue:
            if collection is not None:
                represented_collection_ids.add(int(collection.id))
                result.append(_action(
                    key=f"invoice:{invoice_id}:collection",
                    priority="critical",
                    category="Cartera",
                    title="Ejecutar gestión de cartera vencida",
                    subject=subject,
                    detail=f"Existe una gestión pendiente: {collection.action_type} por {collection.channel}. No se marca como ejecutada automáticamente.",
                    href="#cartera",
                    due_date=due_date,
                    amount=amount,
                    amount_label=amount_label,
                ))
            elif semantics == INVOICE_BASE_BEFORE_TAX:
                result.append(_action(
                    key=f"invoice:{invoice_id}:overdue-tax-base",
                    priority="critical",
                    category="Cartera",
                    title="Resolver cobro vencido con total aún no determinado",
                    subject=subject,
                    detail="La base contractual está vencida, pero el sistema no inventa impuesto ni total final sin autoridad tributaria persistida.",
                    href="#cobros",
                    due_date=due_date,
                    amount=amount,
                    amount_label=amount_label,
                ))
            elif semantics != INVOICE_TOTAL_WITH_TAX:
                result.append(_action(
                    key=f"invoice:{invoice_id}:overdue-legacy",
                    priority="critical",
                    category="Cartera",
                    title="Clasificar y gestionar cobro legacy vencido",
                    subject=subject,
                    detail="El registro está vencido pero no tiene semántica V2.60.6 suficiente para afirmar neto, impuesto o total.",
                    href="#cobros",
                    due_date=due_date,
                    amount=amount,
                    amount_label=amount_label,
                ))
            else:
                result.append(_action(
                    key=f"invoice:{invoice_id}:overdue",
                    priority="critical",
                    category="Cartera",
                    title="Gestionar cobro vencido",
                    subject=subject,
                    detail="El total conocido continúa pendiente después de la fecha de vencimiento registrada.",
                    href="#cobros",
                    due_date=due_date,
                    amount=amount,
                    amount_label=amount_label,
                ))
        elif semantics == INVOICE_BASE_BEFORE_TAX:
            result.append(_action(
                key=f"invoice:{invoice_id}:tax-pending",
                priority="high" if days_to_due is not None and days_to_due <= 7 else "medium",
                category="Cobro",
                title="Completar liquidación tributaria del cobro",
                subject=subject,
                detail="Solo existe base antes de impuesto. El total debe permanecer pendiente hasta contar con una tasa tributaria autoritativa.",
                href="#cobros",
                due_date=due_date,
                amount=amount,
                amount_label=amount_label,
            ))
        elif semantics != INVOICE_TOTAL_WITH_TAX:
            result.append(_action(
                key=f"invoice:{invoice_id}:legacy",
                priority="high",
                category="Cobro",
                title="Clasificar semántica del cobro",
                subject=subject,
                detail="El registro pendiente es legacy; no se agrega a total conocido hasta que exista evidencia suficiente para clasificarlo.",
                href="#cobros",
                due_date=due_date,
                amount=amount,
                amount_label=amount_label,
            ))
        elif days_to_due is not None and 0 <= days_to_due <= 7:
            result.append(_action(
                key=f"invoice:{invoice_id}:upcoming-due",
                priority="high",
                category="Cartera",
                title="Preparar cobro próximo a vencer",
                subject=subject,
                detail=f"El total conocido vence en {days_to_due} día(s).",
                href="#cobros",
                due_date=due_date,
                amount=amount,
                amount_label=amount_label,
            ))

    # Pending collection work can be actionable even when the invoice itself is
    # not overdue (for example a scheduled reminder). Only surface it once its
    # own persisted due date is today or earlier, and never duplicate an action
    # already represented by an overdue invoice above.
    for collection in collection_items:
        if (
            getattr(collection, "status", None) != "Pendiente"
            or getattr(collection, "due_at", None) is None
            or collection.due_at > today
            or int(getattr(collection, "id", 0) or 0) in represented_collection_ids
        ):
            continue
        invoice = getattr(collection, "invoice", None)
        reference = getattr(invoice, "reference", f"Cobro {collection.invoice_id}")
        organization = _organization_label(organization_names, getattr(collection, "organization_id", None))
        result.append(_action(
            key=f"collection:{collection.id}:due",
            priority="high" if collection.due_at == today else "critical",
            category="Cartera",
            title="Ejecutar gestión de cartera programada",
            subject=f"{reference} · {organization}",
            detail=f"{collection.action_type} por {collection.channel} continúa Pendiente y alcanzó su fecha programada.",
            href="#cartera",
            due_date=collection.due_at,
        ))

    result.sort(key=lambda item: (
        _PRIORITY_ORDER[item.priority],
        item.due_date is None,
        item.due_date or date.max,
        item.category,
        item.key,
    ))
    return result


def summarize_revenue_actions(actions: Iterable[RevenueAction]) -> dict[str, int]:
    items = list(actions)
    return {
        "total": len(items),
        "critical": sum(1 for item in items if item.priority == "critical"),
        "high": sum(1 for item in items if item.priority == "high"),
        "medium": sum(1 for item in items if item.priority == "medium"),
    }


__all__ = ["RevenueAction", "build_revenue_action_queue", "summarize_revenue_actions"]
