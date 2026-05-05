from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


UOM = Literal["piece", "kg", "liter", "meter", "box", "pack", "unit"]
Role = Literal["operator", "manager", "admin", "viewer"]


class APIResponse(BaseModel):
    status: str = "success"
    data: Any | None = None
    error: Any | None = None


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    role: Role = "operator"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: EmailStr
    name: str
    role: Role
    status: str
    created_at: datetime


# --- Product ---
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    barcode: Optional[str] = None
    unit_of_measure: UOM
    category: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    reorder_threshold: Optional[int] = None
    supplier_id: Optional[int] = None
    location: Optional[str] = None
    attributes: Optional[dict] = None


class ProductCreate(ProductBase):
    sku: str = Field(min_length=1, max_length=100)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    reorder_threshold: Optional[int] = None
    supplier_id: Optional[int] = None
    location: Optional[str] = None
    attributes: Optional[dict] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    sku: str
    created_at: datetime
    updated_at: datetime


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int
