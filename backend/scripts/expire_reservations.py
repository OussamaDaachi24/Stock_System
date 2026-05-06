"""Daily reservation expiry job.

Run via cron at 03:00 UTC: python -m scripts.expire_reservations
Releases all active reservations whose expiry_timestamp has passed.
"""
from app.db import SessionLocal
from app.models import AuditLog, User
from app.services.reservations import expire_due_reservations


def _system_user_id(db) -> int:
    admin = db.query(User).filter(User.role == "admin").order_by(User.user_id).first()
    if not admin:
        raise RuntimeError("No admin user found to attribute system actions")
    return admin.user_id


def run() -> dict:
    db = SessionLocal()
    try:
        system_uid = _system_user_id(db)
        expired_ids = expire_due_reservations(db, system_user_id=system_uid)
        if expired_ids:
            db.add(
                AuditLog(
                    user_id=system_uid,
                    action="reservation_expiry_job",
                    entity_type="reservation",
                    entity_id=None,
                    new_value={"expired_ids": expired_ids, "count": len(expired_ids)},
                    reason="Daily reservation expiry batch",
                )
            )
        db.commit()
        result = {"expired_count": len(expired_ids), "expired_ids": expired_ids}
        print(result)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run()
