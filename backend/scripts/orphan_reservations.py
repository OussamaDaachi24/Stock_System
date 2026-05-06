"""Orphan reservation cleanup (manual trigger, v1).

Find reservations still 'active' more than 7 days past expiry — these slipped
through the daily expiry job. Log them and (optionally) auto-release.

Usage: python -m scripts.orphan_reservations [--release]
"""
from datetime import datetime, timedelta
import sys

from app.db import SessionLocal
from app.models import AuditLog, Reservation, User
from app.services.reservations import release_reservation


def _system_user_id(db) -> int:
    admin = db.query(User).filter(User.role == "admin").order_by(User.user_id).first()
    if not admin:
        raise RuntimeError("No admin user found to attribute system actions")
    return admin.user_id


def run(auto_release: bool = False) -> dict:
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        orphans = (
            db.query(Reservation)
            .filter(Reservation.status == "active")
            .filter(Reservation.expiry_timestamp < cutoff)
            .all()
        )
        orphan_ids = [r.reservation_id for r in orphans]

        if orphans:
            db.add(
                AuditLog(
                    user_id=_system_user_id(db),
                    action="orphan_reservations_detected",
                    entity_type="reservation",
                    entity_id=None,
                    new_value={"orphan_ids": orphan_ids, "count": len(orphan_ids)},
                    reason="Orphan cleanup scan",
                )
            )

        released_ids: list[int] = []
        if auto_release and orphans:
            system_uid = _system_user_id(db)
            for res in orphans:
                release_reservation(
                    db,
                    res=res,
                    user_id=system_uid,
                    new_status="expired",
                    reason=f"Orphan auto-release reservation {res.reservation_id}",
                )
                released_ids.append(res.reservation_id)

        db.commit()
        result = {
            "orphan_count": len(orphan_ids),
            "orphan_ids": orphan_ids,
            "released_ids": released_ids,
        }
        print(result)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run(auto_release="--release" in sys.argv)
