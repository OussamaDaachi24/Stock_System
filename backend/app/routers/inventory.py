from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..idempotency import get_cached, request_hash, set_cached
from ..models import (
    LEDGER_TYPES,
    InventoryLedger,
    LowStockAlert,
    Product,
    StockSnapshot,
    User,
)
from ..schemas import (
    APIResponse,
    AdjustmentCreate,
    AdjustmentOut,
    LedgerEntryOut,
    LedgerListOut,
    LowStockProductOut,
    ReconcileResult,
    SnapshotOut,
)
from ..services.inventory import (
    LedgerError,
    append_ledger,
    get_or_create_snapshot,
    recompute_from_ledger,
)


router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


# --- Ledger queries ---
@router.get("/ledger", response_model=APIResponse)
def list_ledger(
    product_id: Optional[int] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if type is not None and type not in LEDGER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Allowed: {LEDGER_TYPES}")

    q = db.query(InventoryLedger)
    if product_id is not None:
        q = q.filter(InventoryLedger.product_id == product_id)
    if type is not None:
        q = q.filter(InventoryLedger.type == type)
    if user_id is not None:
        q = q.filter(InventoryLedger.user_id == user_id)
    if start_date is not None:
        q = q.filter(InventoryLedger.timestamp >= start_date)
    if end_date is not None:
        q = q.filter(InventoryLedger.timestamp <= end_date)

    total = q.count()
    items = (
        q.order_by(InventoryLedger.ledger_id.desc()).limit(limit).offset(offset).all()
    )
    payload = LedgerListOut(
        items=[LedgerEntryOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=payload.model_dump(mode="json"))


# --- Snapshot ---
@router.get("/snapshot", response_model=APIResponse)
def get_snapshot(
    product_id: Optional[int] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if product_id is not None:
        snap = db.query(StockSnapshot).filter_by(product_id=product_id).first()
        if not snap:
            # If product exists but no movements yet, return zeroed snapshot row.
            if not db.get(Product, product_id):
                raise HTTPException(status_code=404, detail="Product not found")
            snap = get_or_create_snapshot(db, product_id)
            db.commit()
        return APIResponse(data=SnapshotOut.model_validate(snap).model_dump(mode="json"))

    q = db.query(StockSnapshot, Product).join(Product, Product.product_id == StockSnapshot.product_id)
    if category is not None:
        q = q.filter(Product.category == category)
    if supplier_id is not None:
        q = q.filter(Product.supplier_id == supplier_id)
    rows = q.all()
    return APIResponse(
        data=[SnapshotOut.model_validate(s).model_dump(mode="json") for s, _p in rows]
    )


# --- Adjustments ---
@router.post("/adjustments", response_model=APIResponse, status_code=201)
def create_adjustment(
    payload: AdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if payload.quantity_delta == 0:
        raise HTTPException(status_code=400, detail="quantity_delta must be non-zero")

    if idempotency_key:
        h = request_hash("POST", "/api/v1/inventory/adjustments", idempotency_key, user.user_id)
        cached = get_cached(h)
        if cached:
            return JSONResponse(status_code=200, content=cached)

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        entry = append_ledger(
            db,
            product_id=payload.product_id,
            type="adjustment",
            quantity_delta=payload.quantity_delta,
            user_id=user.user_id,
            source="adjustment",
            destination="warehouse",
            reason=payload.reason,
            reference=f"approver:{payload.approver_id}" if payload.approver_id else None,
            allow_negative=payload.allow_negative,
        )
    except LedgerError as e:
        db.rollback()
        msg = str(e)
        if "negative" in msg.lower():
            raise HTTPException(
                status_code=422,
                detail={"code": "NEGATIVE_STOCK_NOT_ALLOWED", "message": msg},
            )
        raise HTTPException(status_code=422, detail=msg)

    snap = db.query(StockSnapshot).filter_by(product_id=payload.product_id).first()

    write_audit(
        db,
        user_id=user.user_id,
        action="adjust_stock",
        entity_type="product",
        entity_id=product.product_id,
        new_value={
            "quantity_delta": payload.quantity_delta,
            "reason": payload.reason,
            "approver_id": payload.approver_id,
            "ledger_id": entry.ledger_id,
        },
        reason=payload.reason,
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()

    out = AdjustmentOut(
        ledger_id=entry.ledger_id,
        product_id=product.product_id,
        quantity_delta=payload.quantity_delta,
        reason=payload.reason,
        on_hand=snap.on_hand if snap else 0,
        available=snap.available if snap else 0,
    )
    response = APIResponse(data=out.model_dump())
    if idempotency_key:
        set_cached(h, response.model_dump())
    return response


# --- Reconciliation (manual trigger; nightly job calls same routine) ---
@router.post("/reconcile", response_model=APIResponse)
def reconcile(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    products = db.query(Product).all()
    corrected: list[dict] = []
    for p in products:
        on_hand, reserved, available, last_id = recompute_from_ledger(db, p.product_id)
        snap = get_or_create_snapshot(db, p.product_id)
        if (
            snap.on_hand != on_hand
            or snap.reserved != reserved
            or snap.available != available
        ):
            corrected.append(
                {
                    "product_id": p.product_id,
                    "before": {"on_hand": snap.on_hand, "reserved": snap.reserved, "available": snap.available},
                    "after": {"on_hand": on_hand, "reserved": reserved, "available": available},
                }
            )
            snap.on_hand = on_hand
            snap.reserved = reserved
            snap.available = available
            snap.last_ledger_id = last_id

            write_audit(
                db,
                user_id=user.user_id,
                action="reconciliation_mismatch",
                entity_type="product",
                entity_id=p.product_id,
                old_value=corrected[-1]["before"],
                new_value=corrected[-1]["after"],
                reason="Snapshot recomputed from ledger",
            )

    db.commit()
    result = ReconcileResult(
        products_checked=len(products),
        mismatches_found=len(corrected),
        corrected=corrected,
    )
    return APIResponse(data=result.model_dump())


# --- Low-stock ---
@router.get("/low-stock", response_model=APIResponse)
def low_stock(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    raise_alerts: bool = Query(False, description="Persist alert rows (deduped per day)"),
):
    rows = (
        db.query(Product, StockSnapshot)
        .outerjoin(StockSnapshot, StockSnapshot.product_id == Product.product_id)
        .filter(Product.reorder_threshold.isnot(None))
        .all()
    )
    breached: list[LowStockProductOut] = []
    today = date.today().isoformat()
    for product, snap in rows:
        on_hand = snap.on_hand if snap else 0
        if on_hand < (product.reorder_threshold or 0):
            breached.append(
                LowStockProductOut(
                    product_id=product.product_id,
                    sku=product.sku,
                    name=product.name,
                    on_hand=on_hand,
                    reorder_threshold=product.reorder_threshold,
                )
            )
            if raise_alerts:
                exists = (
                    db.query(LowStockAlert)
                    .filter_by(product_id=product.product_id, alert_date=today)
                    .first()
                )
                if not exists:
                    db.add(
                        LowStockAlert(
                            product_id=product.product_id,
                            on_hand=on_hand,
                            reorder_threshold=product.reorder_threshold,
                            alert_date=today,
                        )
                    )
    if raise_alerts:
        db.commit()
    return APIResponse(data=[b.model_dump() for b in breached])
