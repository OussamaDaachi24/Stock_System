"""Receiving service: PO/receipt line matching, discrepancy detection,
put-away task generation. All ledger writes go through inventory.append_ledger
to preserve append-only semantics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import (
    POLine,
    Product,
    PurchaseOrder,
    PutAwayTask,
    Receipt,
    ReceiptLine,
)
from .inventory import append_ledger


def match_po_line(db: Session, po: PurchaseOrder, product_id: int) -> Optional[POLine]:
    for line in po.lines:
        if line.product_id == product_id and line.received_quantity < line.quantity:
            return line
    # fall back to any line with matching product even if filled (over-receipt)
    for line in po.lines:
        if line.product_id == product_id:
            return line
    return None


def post_receipt_line(
    db: Session,
    *,
    receipt: Receipt,
    product: Product,
    quantity: int,
    user_id: int,
    lot_batch: Optional[str] = None,
    serial_numbers: Optional[list[str]] = None,
    location: Optional[str] = None,
    po: Optional[PurchaseOrder] = None,
) -> tuple[ReceiptLine, dict | None]:
    """Insert receipt line + ledger entry; return (line, discrepancy_dict|None).

    Discrepancy types:
      - 'over'   : line on PO but quantity exceeds outstanding amount
      - 'unknown': no matching line on PO (unknown item)
      - 'under'  : detected at receipt completion, not per-line
    """
    discrepancy: dict | None = None
    po_line: Optional[POLine] = None

    if po is not None:
        po_line = match_po_line(db, po, product.product_id)
        if po_line is None:
            discrepancy = {
                "product_id": product.product_id,
                "type": "unknown",
                "expected": 0,
                "received": quantity,
                "note": "Item not on PO; flagged for manager review",
            }
        else:
            outstanding = po_line.quantity - po_line.received_quantity
            if quantity > outstanding:
                discrepancy = {
                    "product_id": product.product_id,
                    "type": "over",
                    "expected": outstanding,
                    "received": quantity,
                    "note": "Received exceeds outstanding PO quantity",
                }
            po_line.received_quantity = po_line.received_quantity + quantity

    entry = append_ledger(
        db,
        product_id=product.product_id,
        type="receiving",
        quantity_delta=quantity,
        user_id=user_id,
        source=f"supplier:{receipt.supplier_id}" if receipt.supplier_id else "supplier",
        destination="receiving",
        reference=f"receipt:{receipt.receipt_id}",
        reason=f"Receipt {receipt.receipt_id}" + (f" / PO {po.po_id}" if po else ""),
    )

    line = ReceiptLine(
        receipt_id=receipt.receipt_id,
        product_id=product.product_id,
        po_line_id=po_line.po_line_id if po_line else None,
        quantity=quantity,
        lot_batch=lot_batch,
        serial_numbers=serial_numbers,
        location=location,
        ledger_id=entry.ledger_id,
        flagged=discrepancy["type"] if discrepancy else None,
    )
    db.add(line)
    db.flush()
    return line, discrepancy


def update_po_status(po: PurchaseOrder) -> None:
    """Recompute PO status from line received_quantity."""
    if not po.lines:
        return
    if all(line.received_quantity >= line.quantity for line in po.lines):
        po.status = "closed"
    elif any(line.received_quantity > 0 for line in po.lines):
        po.status = "partial"
    else:
        po.status = "open"


def detect_under_receipt(po: PurchaseOrder) -> list[dict]:
    """Return per-line under-receipt entries (PO line not fully received)."""
    out = []
    for line in po.lines:
        if line.received_quantity < line.quantity:
            out.append(
                {
                    "product_id": line.product_id,
                    "type": "under",
                    "expected": line.quantity,
                    "received": line.received_quantity,
                    "note": "PO line not fully received",
                }
            )
    return out


def generate_put_away_tasks(db: Session, receipt: Receipt) -> list[PutAwayTask]:
    """Generate one task per receipt line on completion."""
    tasks = []
    for line in receipt.lines:
        task = PutAwayTask(
            receipt_line_id=line.receipt_line_id,
            product_id=line.product_id,
            quantity=line.quantity,
            from_location="receiving",
            to_location=line.location,
            status="pending",
        )
        db.add(task)
        tasks.append(task)
    db.flush()
    return tasks


def complete_receipt(db: Session, receipt: Receipt) -> list[PutAwayTask]:
    receipt.status = "completed"
    receipt.completed_at = datetime.utcnow()
    if receipt.po_id:
        po = db.get(PurchaseOrder, receipt.po_id)
        if po is not None:
            update_po_status(po)
    return generate_put_away_tasks(db, receipt)
