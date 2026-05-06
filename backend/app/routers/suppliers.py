from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Supplier, User
from ..schemas import APIResponse, SupplierCreate, SupplierOut, SupplierUpdate


router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


def _serialize(s: Supplier) -> dict:
    return {
        "supplier_id": s.supplier_id,
        "name": s.name,
        "contact_email": s.contact_email,
        "contact_phone": s.contact_phone,
        "city": s.city,
        "country": s.country,
        "active": s.active,
    }


@router.post("", response_model=APIResponse, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    s = Supplier(**payload.model_dump())
    db.add(s)
    db.flush()
    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="supplier",
        entity_id=s.supplier_id,
        new_value=_serialize(s),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(s)
    return APIResponse(data=SupplierOut.model_validate(s).model_dump(mode="json"))


@router.get("", response_model=APIResponse)
def list_suppliers(
    search: Optional[str] = None,
    active: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Supplier)
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import func as _f
        q = q.filter(_f.lower(Supplier.name).like(like))
    if active is not None:
        q = q.filter(Supplier.active == active)
    total = q.count()
    rows = q.order_by(Supplier.supplier_id.desc()).limit(limit).offset(offset).all()
    return APIResponse(
        data={
            "items": [SupplierOut.model_validate(r).model_dump(mode="json") for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{supplier_id}", response_model=APIResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    s = db.get(Supplier, supplier_id)
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return APIResponse(data=SupplierOut.model_validate(s).model_dump(mode="json"))


@router.put("/{supplier_id}", response_model=APIResponse)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    s = db.get(Supplier, supplier_id)
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    old = _serialize(s)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.flush()
    write_audit(
        db,
        user_id=user.user_id,
        action="update",
        entity_type="supplier",
        entity_id=s.supplier_id,
        old_value=old,
        new_value=_serialize(s),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(s)
    return APIResponse(data=SupplierOut.model_validate(s).model_dump(mode="json"))
