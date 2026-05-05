"""Inventory service: append-only ledger writes + snapshot updates.

Domain rules (CLAUDE.md):
- Ledger entries are immutable. This service only INSERTs.
- Stock snapshot is a denormalized cache; we update it in the same transaction
  as the ledger insert so reads stay consistent.
- Snapshot-only fields:
    on_hand  : sum of all quantity_delta for the product
    reserved : magnitude of active reservations
                 - reservation entries decrement available; release/expire restore it
    available = on_hand - reserved
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import LEDGER_TYPES, InventoryLedger, StockSnapshot


class LedgerError(ValueError):
    pass


def get_or_create_snapshot(db: Session, product_id: int, *, lock: bool = False) -> StockSnapshot:
    q = db.query(StockSnapshot).filter_by(product_id=product_id)
    if lock and db.bind.dialect.name != "sqlite":
        q = q.with_for_update()
    snap = q.first()
    if snap is None:
        snap = StockSnapshot(product_id=product_id, on_hand=0, reserved=0, available=0)
        db.add(snap)
        db.flush()
    return snap


def append_ledger(
    db: Session,
    *,
    product_id: int,
    type: str,
    quantity_delta: int,
    user_id: int,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    reference: Optional[str] = None,
    reason: Optional[str] = None,
    update_snapshot: bool = True,
    allow_negative: bool = False,
) -> InventoryLedger:
    """Append a ledger entry and (optionally) update the snapshot atomically.

    Caller is responsible for the surrounding transaction. We flush so callers
    can read back the ledger_id, but we do not commit.
    """
    if type not in LEDGER_TYPES:
        raise LedgerError(f"Invalid ledger type: {type}")
    if quantity_delta is None:
        raise LedgerError("quantity_delta is required")

    snap = get_or_create_snapshot(db, product_id, lock=update_snapshot)

    if update_snapshot:
        new_on_hand = snap.on_hand
        new_reserved = snap.reserved

        if type == "reservation":
            new_reserved = snap.reserved + abs(quantity_delta)
        elif type in ("release",):
            new_reserved = max(0, snap.reserved - abs(quantity_delta))
        else:
            new_on_hand = snap.on_hand + quantity_delta

        new_available = new_on_hand - new_reserved
        if not allow_negative and new_available < 0:
            raise LedgerError("Resulting stock would be negative")

    entry = InventoryLedger(
        product_id=product_id,
        type=type,
        quantity_delta=quantity_delta,
        source=source,
        destination=destination,
        reference=reference,
        user_id=user_id,
        reason=reason,
    )
    db.add(entry)
    db.flush()

    if update_snapshot:
        snap.on_hand = new_on_hand
        snap.reserved = new_reserved
        snap.available = new_available
        snap.last_ledger_id = entry.ledger_id
        db.flush()

    return entry


def recompute_from_ledger(db: Session, product_id: int) -> tuple[int, int, int, Optional[int]]:
    """Recompute (on_hand, reserved, available, last_ledger_id) from the ledger.

    on_hand  = SUM(quantity_delta) for non-reservation/release types
    reserved = SUM(active reservation deltas) - SUM(release deltas)
               (computed as: |reservation deltas| - |release deltas|, floored at 0)
    """
    on_hand_q = (
        db.query(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
        .filter(InventoryLedger.product_id == product_id)
        .filter(~InventoryLedger.type.in_(["reservation", "release"]))
    )
    on_hand = int(on_hand_q.scalar() or 0)

    reserved_q = (
        db.query(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
        .filter(InventoryLedger.product_id == product_id)
        .filter(InventoryLedger.type == "reservation")
    )
    released_q = (
        db.query(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
        .filter(InventoryLedger.product_id == product_id)
        .filter(InventoryLedger.type == "release")
    )
    reserved = max(0, abs(int(reserved_q.scalar() or 0)) - abs(int(released_q.scalar() or 0)))

    last_id = (
        db.query(func.max(InventoryLedger.ledger_id))
        .filter(InventoryLedger.product_id == product_id)
        .scalar()
    )

    return on_hand, reserved, on_hand - reserved, last_id
