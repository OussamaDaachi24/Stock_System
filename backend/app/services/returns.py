"""Returns service: intake, disposition, and credit memo flow.

Domain rules:
- Intake: stock increases immediately via append-only ledger entry (type='return').
- Validation: quantity must be > 0 and <= current on_hand snapshot for the product
  (we cannot return more than we currently track as held).
- Disposition: 'restock' is a no-op for stock (intake already added). 'scrap'
  emits a second ledger entry (type='scrap', qty_delta=-qty) to remove stock.
  'repair' is intake-only for v1 (stock stays in 'on_hand' until further policy
  is defined).
- Credit memos are draft on creation; issued via explicit endpoint.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from ..models import CreditMemo, Product, Return, StockSnapshot
from .inventory import LedgerError, append_ledger, get_or_create_snapshot


def create_return(
    db: Session,
    *,
    product: Product,
    quantity: int,
    reason: str,
    user_id: int,
    reference: Optional[str] = None,
    receiving_notes: Optional[str] = None,
) -> Return:
    if quantity <= 0:
        raise LedgerError("Return quantity must be positive")

    snap = get_or_create_snapshot(db, product.product_id, lock=True)
    if quantity > snap.on_hand:
        raise LedgerError(
            f"Cannot return {quantity}; only {snap.on_hand} on hand for product {product.product_id}"
        )

    ret = Return(
        product_id=product.product_id,
        quantity=quantity,
        reason=reason,
        reference=reference,
        return_user_id=user_id,
        receiving_notes=receiving_notes,
        status="intake",
    )
    db.add(ret)
    db.flush()

    entry = append_ledger(
        db,
        product_id=product.product_id,
        type="return",
        quantity_delta=quantity,
        user_id=user_id,
        source="customer",
        destination="warehouse",
        reference=f"return:{ret.return_id}",
        reason=f"Return {ret.return_id} ({reason})",
    )
    ret.ledger_id = entry.ledger_id
    db.flush()
    return ret


def apply_disposition(
    db: Session,
    *,
    ret: Return,
    disposition: str,
    user_id: int,
    notes: Optional[str] = None,
    credit_amount: Optional[Decimal] = None,
) -> tuple[Return, Optional[CreditMemo]]:
    if ret.status == "closed":
        raise LedgerError("Return already closed")
    if disposition not in ("restock", "scrap", "repair"):
        raise LedgerError(f"Invalid disposition: {disposition}")

    ret.disposition = disposition
    ret.disposition_notes = notes
    ret.status = "disposition_decided"

    if disposition == "scrap":
        scrap_entry = append_ledger(
            db,
            product_id=ret.product_id,
            type="scrap",
            quantity_delta=-ret.quantity,
            user_id=user_id,
            source="warehouse",
            destination="scrap",
            reference=f"return:{ret.return_id}",
            reason=f"Scrap from return {ret.return_id}",
        )
        ret.scrap_ledger_id = scrap_entry.ledger_id

    memo: Optional[CreditMemo] = None
    if credit_amount is not None:
        memo = CreditMemo(
            return_id=ret.return_id,
            amount=credit_amount,
            status="draft",
        )
        db.add(memo)
        db.flush()
        ret.credit_memo_id = memo.credit_memo_id

    ret.status = "closed"
    ret.closed_at = datetime.utcnow()
    db.flush()
    return ret, memo


def issue_credit_memo(db: Session, memo: CreditMemo) -> CreditMemo:
    if memo.status != "draft":
        raise LedgerError(f"Cannot issue memo in status {memo.status}")
    memo.status = "issued"
    memo.issued_date = datetime.utcnow()
    db.flush()
    return memo
