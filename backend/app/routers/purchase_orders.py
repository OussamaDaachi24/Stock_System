from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import POLine, Product, PurchaseOrder, Supplier, User
from ..schemas import APIResponse, PurchaseOrderCreate, PurchaseOrderOut


router = APIRouter(prefix="/api/v1/purchase-orders", tags=["purchase-orders"])


@router.post("", response_model=APIResponse, status_code=201)
def create_po(
    payload: PurchaseOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if db.query(PurchaseOrder).filter_by(po_number=payload.po_number).first():
        raise HTTPException(status_code=409, detail="po_number already exists")

    for line in payload.lines:
        if not db.get(Product, line.product_id):
            raise HTTPException(
                status_code=404, detail=f"Product {line.product_id} not found"
            )

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        po_number=payload.po_number,
        expected_delivery_date=payload.expected_delivery_date,
        notes=payload.notes,
        status="open",
        created_by=user.user_id,
    )
    db.add(po)
    db.flush()

    for line in payload.lines:
        db.add(
            POLine(
                po_id=po.po_id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                received_quantity=0,
            )
        )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Constraint violation")

    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="purchase_order",
        entity_id=po.po_id,
        new_value={"po_number": po.po_number, "supplier_id": po.supplier_id, "lines": len(payload.lines)},
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(po)
    return APIResponse(data=PurchaseOrderOut.model_validate(po).model_dump(mode="json"))


@router.get("", response_model=APIResponse)
def list_pos(
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if supplier_id is not None:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    total = q.count()
    rows = q.order_by(PurchaseOrder.po_id.desc()).limit(limit).offset(offset).all()
    return APIResponse(
        data={
            "items": [PurchaseOrderOut.model_validate(p).model_dump(mode="json") for p in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{po_id}", response_model=APIResponse)
def get_po(
    po_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return APIResponse(data=PurchaseOrderOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/cancel", response_model=APIResponse)
def cancel_po(
    po_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status in ("closed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"PO already {po.status}")
    old = po.status
    po.status = "cancelled"
    write_audit(
        db,
        user_id=user.user_id,
        action="cancel",
        entity_type="purchase_order",
        entity_id=po.po_id,
        old_value={"status": old},
        new_value={"status": "cancelled"},
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(po)
    return APIResponse(data=PurchaseOrderOut.model_validate(po).model_dump(mode="json"))
