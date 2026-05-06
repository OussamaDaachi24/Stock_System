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


# --- Suppliers ---
class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[int] = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    supplier_id: int
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    active: int
    created_at: datetime


# --- Purchase Orders ---
POStatus = Literal["open", "partial", "closed", "cancelled"]


class POLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Optional[Decimal] = None


class POLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    po_line_id: int
    po_id: int
    product_id: int
    quantity: int
    received_quantity: int
    unit_price: Optional[Decimal] = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    po_number: str = Field(min_length=1, max_length=100)
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    lines: list[POLineIn] = Field(min_length=1)


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    po_id: int
    supplier_id: int
    po_number: str
    status: POStatus
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    lines: list[POLineOut] = []


# --- Receipts ---
ReceiptStatus = Literal["open", "partial", "completed"]


class ReceiptLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    lot_batch: Optional[str] = None
    serial_numbers: Optional[list[str]] = None
    location: Optional[str] = None


class ReceiptLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    receipt_line_id: int
    receipt_id: int
    product_id: int
    po_line_id: Optional[int] = None
    quantity: int
    lot_batch: Optional[str] = None
    serial_numbers: Optional[list[str]] = None
    location: Optional[str] = None
    ledger_id: Optional[int] = None
    flagged: Optional[str] = None


class ReceiptCreate(BaseModel):
    po_id: Optional[int] = None
    supplier_id: Optional[int] = None
    packing_info: Optional[dict] = None
    lines: list[ReceiptLineIn] = Field(min_length=1)


class DiscrepancyOut(BaseModel):
    product_id: int
    type: str  # over | under | unknown
    expected: Optional[int] = None
    received: int
    note: Optional[str] = None


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    receipt_id: int
    po_id: Optional[int] = None
    supplier_id: Optional[int] = None
    receiving_user_id: int
    status: ReceiptStatus
    packing_info: Optional[dict] = None
    discrepancies: Optional[list[dict]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    lines: list[ReceiptLineOut] = []


# --- Returns ---
ReturnStatus = Literal["intake", "inspection", "disposition_decided", "closed"]
ReturnReason = Literal["defective", "wrong_item", "customer_request", "expired", "other"]
ReturnDisposition = Literal["restock", "scrap", "repair"]


class ReturnCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    reason: ReturnReason
    reference: Optional[str] = None
    receiving_notes: Optional[str] = None


class ReturnDispositionUpdate(BaseModel):
    disposition: ReturnDisposition
    disposition_notes: Optional[str] = None
    credit_amount: Optional[Decimal] = None


CreditMemoStatus = Literal["draft", "issued", "applied"]


class CreditMemoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    credit_memo_id: int
    return_id: int
    amount: Decimal
    issued_date: Optional[datetime] = None
    status: CreditMemoStatus
    created_at: datetime


class ReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    return_id: int
    product_id: int
    quantity: int
    reason: ReturnReason
    reference: Optional[str] = None
    return_user_id: int
    receiving_notes: Optional[str] = None
    status: ReturnStatus
    disposition: Optional[ReturnDisposition] = None
    disposition_notes: Optional[str] = None
    ledger_id: Optional[int] = None
    scrap_ledger_id: Optional[int] = None
    credit_memo_id: Optional[int] = None
    created_at: datetime
    closed_at: Optional[datetime] = None


class ReturnListOut(BaseModel):
    items: list[ReturnOut]
    total: int
    limit: int
    offset: int


# --- Reservations ---
ReservationStatus = Literal["active", "released", "expired"]


class ReservationCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    reference: Optional[str] = None
    expiry_days: int = Field(default=30, ge=1, le=365)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reservation_id: int
    product_id: int
    quantity: int
    reference: Optional[str] = None
    status: ReservationStatus
    expiry_timestamp: datetime
    reserve_ledger_id: Optional[int] = None
    release_ledger_id: Optional[int] = None
    created_at: datetime
    released_at: Optional[datetime] = None
    created_by: int


class ReservationListOut(BaseModel):
    items: list[ReservationOut]
    total: int
    limit: int
    offset: int


class PutAwayTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task_id: int
    receipt_line_id: int
    product_id: int
    quantity: int
    from_location: str
    to_location: Optional[str] = None
    status: str
    created_at: datetime
