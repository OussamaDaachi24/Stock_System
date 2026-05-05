from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import User
from ..schemas import APIResponse, LoginRequest, TokenResponse, UserCreate, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/login", response_model=APIResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User inactive")

    user.last_login = datetime.utcnow()
    db.commit()

    tokens = TokenResponse(
        access_token=create_access_token(user.user_id, user.role),
        refresh_token=create_refresh_token(user.user_id, user.role),
    )
    return APIResponse(data={"tokens": tokens.model_dump(), "user": UserOut.model_validate(user).model_dump(mode="json")})


@router.post("/refresh", response_model=APIResponse)
def refresh(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing refresh token")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User inactive")
    return APIResponse(
        data=TokenResponse(
            access_token=create_access_token(user.user_id, user.role),
            refresh_token=create_refresh_token(user.user_id, user.role),
        ).model_dump()
    )


@router.get("/me", response_model=APIResponse)
def me(user: User = Depends(get_current_user)):
    return APIResponse(data=UserOut.model_validate(user).model_dump(mode="json"))


@admin_router.post("/users", response_model=APIResponse, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(
        email=payload.email.lower(),
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return APIResponse(data=UserOut.model_validate(user).model_dump(mode="json"))


@admin_router.get("/users", response_model=APIResponse)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    users = db.query(User).order_by(User.user_id).all()
    return APIResponse(data=[UserOut.model_validate(u).model_dump(mode="json") for u in users])
