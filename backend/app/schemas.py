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


# --- Inventory ---
LedgerType = Literal[
    "receiving", "sales", "adjustment", "transfer", "return", "reservation", "release", "scrap"
]


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ledger_id: int
    product_id: int
    type: str
    quantity_delta: int
    source: Optional[str] = None
    destination: Optional[str] = None
    reference: Optional[str] = None
    user_id: int
    reason: Optional[str] = None
    timestamp: datetime


class LedgerListOut(BaseModel):
    items: list[LedgerEntryOut]
    total: int
    limit: int
    offset: int


class AdjustmentCreate(BaseModel):
    product_id: int
    quantity_delta: int = Field(description="Positive or negative; non-zero")
    reason: str = Field(min_length=1, max_length=500)
    approver_id: Optional[int] = None
    allow_negative: bool = False


class AdjustmentOut(BaseModel):
    ledger_id: int
    product_id: int
    quantity_delta: int
    reason: str
    on_hand: int
    available: int


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    snapshot_id: int
    product_id: int
    on_hand: int
    reserved: int
    available: int
    last_ledger_id: Optional[int] = None
    snapshot_timestamp: datetime
    updated_at: datetime


class LowStockProductOut(BaseModel):
    product_id: int
    sku: str
    name: str
    on_hand: int
    reorder_threshold: int


class ReconcileResult(BaseModel):
    products_checked: int
    mismatches_found: int
    corrected: list[dict]
