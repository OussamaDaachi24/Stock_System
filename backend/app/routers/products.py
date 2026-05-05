from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import serialize_product, write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..idempotency import get_cached, request_hash, set_cached
from ..models import Product, User
from ..schemas import (
    APIResponse,
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)


router = APIRouter(prefix="/api/v1/products", tags=["products"])


def _check_unique(db: Session, sku: str, barcode: Optional[str], exclude_id: Optional[int] = None):
    q = db.query(Product).filter(func.upper(Product.sku) == sku.upper())
    if exclude_id:
        q = q.filter(Product.product_id != exclude_id)
    if q.first():
        raise HTTPException(status_code=409, detail="SKU already exists")
    if barcode:
        q = db.query(Product).filter(Product.barcode == barcode)
        if exclude_id:
            q = q.filter(Product.product_id != exclude_id)
        if q.first():
            raise HTTPException(status_code=409, detail="Barcode already exists")


@router.post("", response_model=APIResponse, status_code=201)
def create_product(
    payload: ProductCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        h = request_hash("POST", "/api/v1/products", idempotency_key, user.user_id)
        cached = get_cached(h)
        if cached:
            return JSONResponse(status_code=200, content=cached)

    _check_unique(db, payload.sku, payload.barcode)

    product = Product(
        sku=payload.sku,
        name=payload.name,
        barcode=payload.barcode,
        unit_of_measure=payload.unit_of_measure,
        category=payload.category,
        cost_price=payload.cost_price,
        sell_price=payload.sell_price,
        reorder_threshold=payload.reorder_threshold,
        supplier_id=payload.supplier_id,
        location=payload.location,
        attributes=payload.attributes,
        created_by=user.user_id,
        updated_by=user.user_id,
    )
    db.add(product)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate SKU or barcode")

    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="product",
        entity_id=product.product_id,
        new_value=serialize_product(product),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(product)

    response = APIResponse(data=ProductOut.model_validate(product).model_dump(mode="json"))
    if idempotency_key:
        set_cached(h, response.model_dump())
    return response


@router.get("", response_model=APIResponse)
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Product)
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(
            or_(
                func.lower(Product.sku).like(like),
                func.lower(Product.name).like(like),
                func.lower(func.coalesce(Product.barcode, "")).like(like),
            )
        )
    if category:
        q = q.filter(Product.category == category)
    if supplier_id is not None:
        q = q.filter(Product.supplier_id == supplier_id)

    total = q.count()
    items = q.order_by(Product.product_id.desc()).limit(limit).offset(offset).all()
    payload = ProductListOut(
        items=[ProductOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=payload.model_dump(mode="json"))


@router.get("/{product_id}", response_model=APIResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return APIResponse(data=ProductOut.model_validate(product).model_dump(mode="json"))


@router.put("/{product_id}", response_model=APIResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old = serialize_product(product)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)
    product.updated_by = user.user_id

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Constraint violation")

    write_audit(
        db,
        user_id=user.user_id,
        action="update",
        entity_type="product",
        entity_id=product.product_id,
        old_value=old,
        new_value=serialize_product(product),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(product)
    return APIResponse(data=ProductOut.model_validate(product).model_dump(mode="json"))
