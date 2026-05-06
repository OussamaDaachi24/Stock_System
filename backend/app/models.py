from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    JSON,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="operator")
    status = Column(String(50), nullable=False, default="active")
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    barcode = Column(String(100), nullable=True)
    unit_of_measure = Column(String(50), nullable=False)
    category = Column(String(100), nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=True)
    sell_price = Column(Numeric(10, 2), nullable=True)
    reorder_threshold = Column(Integer, nullable=True)
    supplier_id = Column(Integer, nullable=True)
    location = Column(String(100), nullable=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    __table_args__ = (
        Index("idx_products_barcode_unique", "barcode", unique=True, sqlite_where=text("barcode IS NOT NULL")),
        Index("idx_products_category", "category"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(String(1000), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    request_id = Column(String(255), nullable=True)

    __table_args__ = (
        Index("idx_audit_user", "user_id", "timestamp"),
        Index("idx_audit_entity", "entity_type", "entity_id", "timestamp"),
        Index("idx_audit_action", "action", "timestamp"),
    )


LEDGER_TYPES = (
    "receiving",
    "sales",
    "adjustment",
    "transfer",
    "return",
    "reservation",
    "release",
    "scrap",
)


class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"

    ledger_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    type = Column(String(50), nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    source = Column(String(100), nullable=True)
    destination = Column(String(100), nullable=True)
    reference = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    reason = Column(String(500), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ledger_product", "product_id", "timestamp"),
        Index("idx_ledger_type", "type", "timestamp"),
        Index("idx_ledger_reference", "reference"),
        Index("idx_ledger_user", "user_id", "timestamp"),
    )


class StockSnapshot(Base):
    __tablename__ = "stock_snapshot"

    snapshot_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, unique=True)
    on_hand = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    available = Column(Integer, nullable=False, default=0)
    last_ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    snapshot_timestamp = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    payment_terms = Column(String(100), nullable=True)
    notes = Column(String(1000), nullable=True)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_suppliers_name", "name"),
    )


PO_STATUSES = ("open", "partial", "closed", "cancelled")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
    po_number = Column(String(100), nullable=False, unique=True)
    status = Column(String(50), nullable=False, default="open")
    expected_delivery_date = Column(DateTime, nullable=True)
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    lines = relationship(
        "POLine",
        back_populates="po",
        cascade="all, delete-orphan",
        order_by="POLine.po_line_id",
    )

    __table_args__ = (
        Index("idx_po_supplier", "supplier_id"),
        Index("idx_po_status", "status"),
    )


class POLine(Base):
    __tablename__ = "po_lines"

    po_line_id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.po_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    received_quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    po = relationship("PurchaseOrder", back_populates="lines")

    __table_args__ = (
        Index("idx_po_line_po", "po_id"),
        Index("idx_po_line_product", "product_id"),
    )


RECEIPT_STATUSES = ("open", "partial", "completed")


class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.po_id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=True)
    receiving_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(50), nullable=False, default="open")
    packing_info = Column(JSON, nullable=True)
    discrepancies = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    lines = relationship(
        "ReceiptLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptLine.receipt_line_id",
    )

    __table_args__ = (
        Index("idx_receipts_po", "po_id"),
        Index("idx_receipts_status", "status"),
    )


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    receipt_line_id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.receipt_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    po_line_id = Column(Integer, ForeignKey("po_lines.po_line_id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    lot_batch = Column(String(100), nullable=True)
    serial_numbers = Column(JSON, nullable=True)
    location = Column(String(100), nullable=True)
    ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    flagged = Column(String(50), nullable=True)  # 'over', 'unknown', None
    created_at = Column(DateTime, default=datetime.utcnow)

    receipt = relationship("Receipt", back_populates="lines")

    __table_args__ = (
        Index("idx_receipt_line_receipt", "receipt_id"),
        Index("idx_receipt_line_product", "product_id"),
    )


class PutAwayTask(Base):
    __tablename__ = "put_away_tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_line_id = Column(Integer, ForeignKey("receipt_lines.receipt_line_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    from_location = Column(String(100), nullable=False, default="receiving")
    to_location = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_putaway_status", "status"),
    )


RETURN_STATUSES = ("intake", "inspection", "disposition_decided", "closed")
RETURN_REASONS = ("defective", "wrong_item", "customer_request", "expired", "other")
RETURN_DISPOSITIONS = ("restock", "scrap", "repair")


class Return(Base):
    __tablename__ = "returns"

    return_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(String(50), nullable=False)
    reference = Column(String(255), nullable=True)
    return_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    receiving_notes = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="intake")
    disposition = Column(String(50), nullable=True)
    disposition_notes = Column(String(1000), nullable=True)
    ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    scrap_ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    credit_memo_id = Column(
        Integer,
        ForeignKey("credit_memos.credit_memo_id", use_alter=True, name="fk_returns_credit_memo"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_returns_product", "product_id"),
        Index("idx_returns_status", "status"),
        Index("idx_returns_reason", "reason"),
        Index("idx_returns_created", "created_at"),
    )


CREDIT_MEMO_STATUSES = ("draft", "issued", "applied")


class CreditMemo(Base):
    __tablename__ = "credit_memos"

    credit_memo_id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, ForeignKey("returns.return_id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    issued_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_credit_memo_return", "return_id"),
        Index("idx_credit_memo_status", "status"),
    )


RESERVATION_STATUSES = ("active", "released", "expired")


class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    expiry_timestamp = Column(DateTime, nullable=False)
    reserve_ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    release_ledger_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("inventory_ledger.ledger_id"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    __table_args__ = (
        Index("idx_reservations_product", "product_id"),
        Index("idx_reservations_status", "status", "expiry_timestamp"),
        Index("idx_reservations_reference", "reference"),
    )


class LowStockAlert(Base):
    __tablename__ = "low_stock_alerts"

    alert_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    on_hand = Column(Integer, nullable=False)
    reorder_threshold = Column(Integer, nullable=False)
    alert_date = Column(String(10), nullable=False)  # YYYY-MM-DD for daily dedup
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "alert_date", name="uq_low_stock_per_day"),
        Index("idx_low_stock_date", "alert_date"),
    )


EXPORT_JOB_STATUSES = ("queued", "in_progress", "completed", "failed")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    job_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    format = Column(String(20), nullable=False, default="csv")
    filters = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="queued")
    file_path = Column(String(500), nullable=True)
    download_url = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    error = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


BACKUP_STATUSES = ("queued", "running", "completed", "failed")


class Backup(Base):
    __tablename__ = "backups"

    backup_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    file_path = Column(String(500), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    notes = Column(String(500), nullable=True)
    error = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

