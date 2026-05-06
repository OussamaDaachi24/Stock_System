"""Reservations service: atomic create/release + expiry handling.

Domain rules (CLAUDE.md):
- Reserve: SELECT...FOR UPDATE on snapshot; check available >= qty; append
  ledger entry (type='reservation', delta=-qty); insert Reservation row.
- Release: append ledger entry (type='release', delta=+qty); mark reservation
  as released/expired.
- Expiry: scheduled job auto-releases reservations past their expiry_timestamp.
- Idempotency by (product_id, reference): if an active reservation already
  exists with the same reference, return it instead of creating a duplicate.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Reservation
from .inventory import LedgerError, append_ledger


def find_active_by_reference(
    db: Session, *, product_id: int, reference: Optional[str]
) -> Optional[Reservation]:
    if not reference:
        return None
    return (
        db.query(Reservation)
        .filter_by(product_id=product_id, reference=reference, status="active")
        .first()
    )


def create_reservation(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    user_id: int,
    reference: Optional[str] = None,
    expiry_days: int = 30,
) -> Reservation:
    if quantity <= 0:
        raise LedgerError("Reservation quantity must be positive")

    existing = find_active_by_reference(db, product_id=product_id, reference=reference)
    if existing is not None:
        return existing

    entry = append_ledger(
        db,
        product_id=product_id,
        type="reservation",
        quantity_delta=-quantity,
        user_id=user_id,
        source="warehouse",
        destination="reserved",
        reference=reference,
        reason=f"Reservation for {reference}" if reference else "Reservation",
    )

    res = Reservation(
        product_id=product_id,
        quantity=quantity,
        reference=reference,
        status="active",
        expiry_timestamp=datetime.utcnow() + timedelta(days=expiry_days),
        reserve_ledger_id=entry.ledger_id,
        created_by=user_id,
    )
    db.add(res)
    db.flush()
    return res


def release_reservation(
    db: Session,
    *,
    res: Reservation,
    user_id: int,
    new_status: str = "released",
    reason: Optional[str] = None,
) -> Reservation:
    if res.status != "active":
        raise LedgerError(f"Reservation already {res.status}")

    entry = append_ledger(
        db,
        product_id=res.product_id,
        type="release",
        quantity_delta=res.quantity,
        user_id=user_id,
        source="reserved",
        destination="warehouse",
        reference=res.reference or f"reservation:{res.reservation_id}",
        reason=reason or f"Release reservation {res.reservation_id}",
    )

    res.status = new_status
    res.release_ledger_id = entry.ledger_id
    res.released_at = datetime.utcnow()
    db.flush()
    return res


def expire_due_reservations(
    db: Session, *, system_user_id: int, now: Optional[datetime] = None
) -> list[int]:
    """Release all active reservations whose expiry has passed.

    Returns list of expired reservation_ids.
    """
    cutoff = now or datetime.utcnow()
    due = (
        db.query(Reservation)
        .filter(Reservation.status == "active")
        .filter(Reservation.expiry_timestamp < cutoff)
        .all()
    )
    expired_ids: list[int] = []
    for res in due:
        release_reservation(
            db,
            res=res,
            user_id=system_user_id,
            new_status="expired",
            reason=f"Auto-expired reservation {res.reservation_id}",
        )
        expired_ids.append(res.reservation_id)
    return expired_ids
