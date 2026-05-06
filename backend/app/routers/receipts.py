from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..idempotency import get_cached, request_hash, set_cached
from ..models import (
    Product,
    PurchaseOrder,
    PutAwayTask,
    Receipt,
    ReceiptLine,
    User,
)
from ..schemas import (
    APIResponse,
    PutAwayTaskOut,
    ReceiptCreate,
    ReceiptOut,
)
from ..services.inventory import LedgerError
from ..services.receiving import (
    complete_receipt,
    detect_under_receipt,
    post_receipt_line,
    update_po_status,
)


router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])


@router.post("", response_model=APIResponse, status_code=201)
def create_receipt(
    payload: ReceiptCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "operator")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        h = request_hash("POST", "/api/v1/receipts", idempotency_key, user.user_id)
        cached = get_cached(h)
        if cached:
            return JSONResponse(status_code=200, content=cached)

    po: Optional[PurchaseOrder] = None
    if payload.po_id is not None:
        po = db.get(PurchaseOrder, payload.po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        if po.status in ("closed", "cancelled"):
            raise HTTPException(
                status_code=409, detail=f"PO is {po.status}; cannot receive against it"
            )

    supplier_id = payload.supplier_id or (po.supplier_id if po else None)

    receipt = Receipt(
        po_id=payload.po_id,
        supplier_id=supplier_id,
        receiving_user_id=user.user_id,
        status="open",
        packing_info=payload.packing_info,
    )
    db.add(receipt)
    db.flush()

    discrepancies: list[dict] = []
    for in_line in payload.lines:
        product = db.get(Product, in_line.product_id)
        if not product:
            db.rollback()
            raise HTTPException(
                status_code=404, detail=f"Product {in_line.product_id} not found"
            )
        try:
            _, disc = post_receipt_line(
                db,
                receipt=receipt,
                product=product,
                quantity=in_line.quantity,
                user_id=user.user_id,
                lot_batch=in_line.lot_batch,
                serial_numbers=in_line.serial_numbers,
                location=in_line.location,
                po=po,
            )
        except LedgerError as e:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(e))
        if disc:
            discrepancies.append(disc)

    if po is not None:
        update_po_status(po)
    receipt.status = "partial"
    if discrepancies:
        receipt.discrepancies = discrepancies

    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="receipt",
        entity_id=receipt.receipt_id,
        new_value={
            "po_id": receipt.po_id,
            "supplier_id": receipt.supplier_id,
            "lines": len(payload.lines),
            "discrepancies": discrepancies,
        },
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(receipt)

    out = ReceiptOut.model_validate(receipt).model_dump(mode="json")
    out["ledger_ids"] = [l.ledger_id for l in receipt.lines]
    response = APIResponse(data=out)
    payload_out = response.model_dump()
    if idempotency_key:
        set_cached(h, payload_out)
    return response


@router.get("", response_model=APIResponse)
def list_receipts(
    po_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Receipt)
    if po_id is not None:
        q = q.filter(Receipt.po_id == po_id)
    if status:
        q = q.filter(Receipt.status == status)
    total = q.count()
    rows = q.order_by(Receipt.receipt_id.desc()).limit(limit).offset(offset).all()
    return APIResponse(
        data={
            "items": [ReceiptOut.model_validate(r).model_dump(mode="json") for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{receipt_id}", response_model=APIResponse)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return APIResponse(data=ReceiptOut.model_validate(r).model_dump(mode="json"))


@router.post("/{receipt_id}/complete", response_model=APIResponse)
def complete(
    receipt_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "operator")),
):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if receipt.status == "completed":
        raise HTTPException(status_code=409, detail="Receipt already completed")
    if not receipt.lines:
        raise HTTPException(status_code=422, detail="Receipt has no lines")

    under = []
    if receipt.po_id:
        po = db.get(PurchaseOrder, receipt.po_id)
        if po is not None:
            under = detect_under_receipt(po)

    existing = list(receipt.discrepancies or [])
    if under:
        existing.extend(under)
        receipt.discrepancies = existing

    tasks = complete_receipt(db, receipt)

    write_audit(
        db,
        user_id=user.user_id,
        action="complete",
        entity_type="receipt",
        entity_id=receipt.receipt_id,
        new_value={
            "status": "completed",
            "put_away_tasks": len(tasks),
            "under_receipts": len(under),
        },
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(receipt)

    out = ReceiptOut.model_validate(receipt).model_dump(mode="json")
    out["put_away_tasks"] = [
        PutAwayTaskOut.model_validate(t).model_dump(mode="json") for t in tasks
    ]
    return APIResponse(data=out)


@router.get("/{receipt_id}/put-away-tasks", response_model=APIResponse)
def get_put_away_tasks(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    line_ids = [l.receipt_line_id for l in receipt.lines]
    if not line_ids:
        return APIResponse(data=[])
    tasks = (
        db.query(PutAwayTask)
        .filter(PutAwayTask.receipt_line_id.in_(line_ids))
        .order_by(PutAwayTask.task_id)
        .all()
    )
    return APIResponse(
        data=[PutAwayTaskOut.model_validate(t).model_dump(mode="json") for t in tasks]
    )
