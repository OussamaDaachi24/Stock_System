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
