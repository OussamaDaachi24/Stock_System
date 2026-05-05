"""Nightly reconciliation: recompute snapshot from ledger; log mismatches.

Run via cron at 02:00 UTC: python -m scripts.reconcile_stock
"""
from app.db import SessionLocal
from app.models import AuditLog, Product
from app.services.inventory import get_or_create_snapshot, recompute_from_ledger


def run() -> dict:
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        mismatches = []
        for p in products:
            on_hand, reserved, available, last_id = recompute_from_ledger(db, p.product_id)
            snap = get_or_create_snapshot(db, p.product_id)
            if (
                snap.on_hand != on_hand
                or snap.reserved != reserved
                or snap.available != available
            ):
                before = {"on_hand": snap.on_hand, "reserved": snap.reserved, "available": snap.available}
                after = {"on_hand": on_hand, "reserved": reserved, "available": available}
                mismatches.append({"product_id": p.product_id, "before": before, "after": after})
                snap.on_hand = on_hand
                snap.reserved = reserved
                snap.available = available
                snap.last_ledger_id = last_id
                db.add(
                    AuditLog(
                        user_id=1,
                        action="reconciliation_mismatch",
                        entity_type="product",
                        entity_id=p.product_id,
                        old_value=before,
                        new_value=after,
                        reason="Nightly reconciliation",
                    )
                )
        db.commit()
        result = {"products_checked": len(products), "mismatches_found": len(mismatches)}
        print(result)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run()
