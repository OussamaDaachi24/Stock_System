from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..idempotency import get_cached, request_hash, set_cached
from ..models import Product, Reservation, User
from ..schemas import APIResponse, ReservationCreate, ReservationOut
from ..services.inventory import LedgerError
from ..services.reservations import create_reservation, release_reservation


router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


def _serialize(res: Reservation) -> dict:
    return ReservationOut.model_validate(res).model_dump(mode="json")


@router.post("", response_model=APIResponse, status_code=201)
def create_reservation_endpoint(
    payload: ReservationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "operator")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    h = None
    if idempotency_key:
        h = request_hash("POST", "/api/v1/reservations", idempotency_key, user.user_id)
        cached = get_cached(h)
        if cached:
            return JSONResponse(status_code=200, content=cached)

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        res = create_reservation(
            db,
            product_id=payload.product_id,
            quantity=payload.quantity,
            user_id=user.user_id,
            reference=payload.reference,
            expiry_days=payload.expiry_days,
        )
    except LedgerError as e:
        db.rollback()
        msg = str(e)
        if "negative" in msg.lower():
            raise HTTPException(status_code=422, detail="Insufficient stock")
        raise HTTPException(status_code=422, detail=msg)

    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="reservation",
        entity_id=res.reservation_id,
        new_value={
            "product_id": res.product_id,
            "quantity": res.quantity,
            "reference": res.reference,
            "expiry_timestamp": res.expiry_timestamp.isoformat(),
        },
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(res)

    response = APIResponse(data=_serialize(res))
    payload_out = response.model_dump()
    if h:
        set_cached(h, payload_out)
    return response


@router.delete("/{reservation_id}", response_model=APIResponse)
def release_reservation_endpoint(
    reservation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "operator")),
):
    res = db.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")

    old = {"status": res.status}
    try:
        res = release_reservation(db, res=res, user_id=user.user_id)
    except LedgerError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    write_audit(
        db,
        user_id=user.user_id,
        action="release",
        entity_type="reservation",
        entity_id=res.reservation_id,
        old_value=old,
        new_value={"status": res.status, "release_ledger_id": res.release_ledger_id},
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(res)
    return APIResponse(data=_serialize(res))


@router.get("", response_model=APIResponse)
def list_reservations(
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    reference: Optional[str] = None,
    expiry_soon: bool = Query(False, description="Filter to expiry within 7 days"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Reservation)
    if status:
        q = q.filter(Reservation.status == status)
    if product_id is not None:
        q = q.filter(Reservation.product_id == product_id)
    if reference:
        q = q.filter(Reservation.reference == reference)
    if expiry_soon:
        cutoff = datetime.utcnow() + timedelta(days=7)
        q = q.filter(Reservation.status == "active").filter(
            Reservation.expiry_timestamp <= cutoff
        )
    total = q.count()
    rows = q.order_by(Reservation.reservation_id.desc()).limit(limit).offset(offset).all()
    return APIResponse(
        data={
            "items": [_serialize(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{reservation_id}", response_model=APIResponse)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    res = db.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return APIResponse(data=_serialize(res))
