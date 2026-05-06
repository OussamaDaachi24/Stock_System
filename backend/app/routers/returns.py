from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..idempotency import get_cached, request_hash, set_cached
from ..models import CreditMemo, Product, Return, User
from ..schemas import (
    APIResponse,
    CreditMemoOut,
    ReturnCreate,
    ReturnDispositionUpdate,
    ReturnOut,
)
from ..services.inventory import LedgerError
from ..services.returns import apply_disposition, create_return, issue_credit_memo


router = APIRouter(prefix="/api/v1/returns", tags=["returns"])
credit_router = APIRouter(prefix="/api/v1/credit-memos", tags=["credit-memos"])


def _serialize_return(r: Return) -> dict:
    return ReturnOut.model_validate(r).model_dump(mode="json")


@router.post("", response_model=APIResponse, status_code=201)
def create_return_endpoint(
    payload: ReturnCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "operator")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    h = None
    if idempotency_key:
        h = request_hash("POST", "/api/v1/returns", idempotency_key, user.user_id)
        cached = get_cached(h)
        if cached:
            return JSONResponse(status_code=200, content=cached)

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        ret = create_return(
            db,
            product=product,
            quantity=payload.quantity,
            reason=payload.reason,
            user_id=user.user_id,
            reference=payload.reference,
            receiving_notes=payload.receiving_notes,
        )
    except LedgerError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="return",
        entity_id=ret.return_id,
        new_value={
            "product_id": ret.product_id,
            "quantity": ret.quantity,
            "reason": ret.reason,
            "ledger_id": ret.ledger_id,
        },
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(ret)

    response = APIResponse(data=_serialize_return(ret))
    payload_out = response.model_dump()
    if h:
        set_cached(h, payload_out)
    return response


@router.get("", response_model=APIResponse)
def list_returns(
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    reason: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Return)
    if status:
        q = q.filter(Return.status == status)
    if product_id is not None:
        q = q.filter(Return.product_id == product_id)
    if reason:
        q = q.filter(Return.reason == reason)
    if date_from is not None:
        q = q.filter(Return.created_at >= date_from)
    if date_to is not None:
        q = q.filter(Return.created_at <= date_to)
    total = q.count()
    rows = q.order_by(Return.return_id.desc()).limit(limit).offset(offset).all()
    return APIResponse(
        data={
            "items": [_serialize_return(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{return_id}", response_model=APIResponse)
def get_return(
    return_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    r = db.get(Return, return_id)
    if not r:
        raise HTTPException(status_code=404, detail="Return not found")
    return APIResponse(data=_serialize_return(r))


@router.patch("/{return_id}/disposition", response_model=APIResponse)
def set_disposition(
    return_id: int,
    payload: ReturnDispositionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    ret = db.get(Return, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")

    old = {"status": ret.status, "disposition": ret.disposition}
    try:
        ret, memo = apply_disposition(
            db,
            ret=ret,
            disposition=payload.disposition,
            user_id=user.user_id,
            notes=payload.disposition_notes,
            credit_amount=payload.credit_amount,
        )
    except LedgerError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))

    write_audit(
        db,
        user_id=user.user_id,
        action="disposition",
        entity_type="return",
        entity_id=ret.return_id,
        old_value=old,
        new_value={
            "status": ret.status,
            "disposition": ret.disposition,
            "credit_memo_id": ret.credit_memo_id,
            "scrap_ledger_id": ret.scrap_ledger_id,
        },
        reason=payload.disposition_notes,
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(ret)

    out = _serialize_return(ret)
    if memo is not None:
        out["credit_memo"] = CreditMemoOut.model_validate(memo).model_dump(mode="json")
    return APIResponse(data=out)


@router.get("/{return_id}/credit-memo", response_model=APIResponse)
def get_return_credit_memo(
    return_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ret = db.get(Return, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    if not ret.credit_memo_id:
        raise HTTPException(status_code=404, detail="No credit memo for this return")
    memo = db.get(CreditMemo, ret.credit_memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")
    return APIResponse(data=CreditMemoOut.model_validate(memo).model_dump(mode="json"))


@credit_router.post("/{credit_memo_id}/issue", response_model=APIResponse)
def issue_memo_endpoint(
    credit_memo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    memo = db.get(CreditMemo, credit_memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")
    try:
        memo = issue_credit_memo(db, memo)
    except LedgerError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

    write_audit(
        db,
        user_id=user.user_id,
        action="issue",
        entity_type="credit_memo",
        entity_id=memo.credit_memo_id,
        new_value={"status": memo.status, "amount": str(memo.amount)},
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(memo)
    return APIResponse(data=CreditMemoOut.model_validate(memo).model_dump(mode="json"))
