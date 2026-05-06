from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import require_roles
from ..idempotency import _get_store  # type: ignore
from ..models import (
    Backup,
    InventoryLedger,
    Product,
    Receipt,
    Reservation,
    Return,
    StockSnapshot,
    User,
)
from ..schemas import (
    APIResponse,
    BackupOut,
    HealthOut,
    MetricsOut,
    RestoreRequest,
)
from ..services.backup import queue_backup, restore_backup, run_backup
from ..config import settings


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/backups", response_model=APIResponse, status_code=202)
def trigger_backup(
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    b = queue_backup(db, user_id=user.user_id, notes=notes)
    b = run_backup(db, b)
    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="backup",
        entity_id=None,
        new_value={"backup_id": b.backup_id, "status": b.status, "size_bytes": b.size_bytes},
        reason=notes,
    )
    db.commit()
    return APIResponse(data=BackupOut.model_validate(b).model_dump(mode="json"))


@router.get("/backups", response_model=APIResponse)
def list_backups(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    rows = db.query(Backup).order_by(Backup.created_at.desc()).limit(100).all()
    return APIResponse(
        data=[BackupOut.model_validate(b).model_dump(mode="json") for b in rows]
    )


@router.post("/restore", response_model=APIResponse)
def restore(
    payload: RestoreRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    b = db.get(Backup, payload.backup_id)
    if not b:
        raise HTTPException(status_code=404, detail="Backup not found")
    try:
        result = restore_backup(db, b, verify=payload.verify)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    write_audit(
        db,
        user_id=user.user_id,
        action="restore",
        entity_type="backup",
        entity_id=None,
        new_value={"backup_id": b.backup_id, "result": result},
    )
    db.commit()
    return APIResponse(data={"backup_id": b.backup_id, **result})


# --- Health & Metrics (public-ish; metrics requires auth) ---
health_router = APIRouter(prefix="/api/v1", tags=["health"])


@health_router.get("/health/full", response_model=APIResponse)
def health_full(db: Session = Depends(get_db)):
    db_ok = "ok"
    try:
        db.execute(func.count()).scalar()  # cheap noop
    except Exception:
        db_ok = "error"

    redis_ok = "memory"
    try:
        store = _get_store()
        if hasattr(store, "ping"):
            store.ping()
            redis_ok = "ok"
    except Exception:
        redis_ok = "error"

    out = HealthOut(service="stock-system", status="ok", db=db_ok, redis=redis_ok)
    return APIResponse(data=out.model_dump())


@health_router.get("/metrics", response_model=APIResponse)
def metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
):
    products = db.query(func.count(Product.product_id)).scalar() or 0
    ledger = db.query(func.count(InventoryLedger.ledger_id)).scalar() or 0
    active_res = (
        db.query(func.count(Reservation.reservation_id))
        .filter(Reservation.status == "active")
        .scalar()
        or 0
    )
    open_receipts = (
        db.query(func.count(Receipt.receipt_id))
        .filter(Receipt.status != "completed")
        .scalar()
        or 0
    )
    pending_returns = (
        db.query(func.count(Return.return_id))
        .filter(Return.status != "closed")
        .scalar()
        or 0
    )
    low = (
        db.query(func.count(Product.product_id))
        .outerjoin(StockSnapshot, StockSnapshot.product_id == Product.product_id)
        .filter(Product.reorder_threshold.isnot(None))
        .filter(func.coalesce(StockSnapshot.on_hand, 0) < Product.reorder_threshold)
        .scalar()
        or 0
    )

    scheme = settings.DATABASE_URL.split(":", 1)[0]
    out = MetricsOut(
        products=int(products),
        ledger_entries=int(ledger),
        active_reservations=int(active_res),
        open_receipts=int(open_receipts),
        pending_returns=int(pending_returns),
        low_stock=int(low),
        db_url_scheme=scheme,
    )
    return APIResponse(data=out.model_dump())
