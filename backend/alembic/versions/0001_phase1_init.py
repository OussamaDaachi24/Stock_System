"""Phase 1 init: users, products, audit_logs.

Revision ID: 0001_phase1_init
Revises:
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_phase1_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="operator"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])

    op.create_table(
        "products",
        sa.Column("product_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sku", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("unit_of_measure", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sell_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("reorder_threshold", sa.Integer, nullable=True),
        sa.Column("supplier_id", sa.Integer, nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("attributes", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.user_id"), nullable=True),
    )
    op.create_index(
        "idx_products_barcode_unique",
        "products",
        ["barcode"],
        unique=True,
        postgresql_where=sa.text("barcode IS NOT NULL"),
    )
    op.create_index("idx_products_category", "products", ["category"])

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("old_value", sa.JSON, nullable=True),
        sa.Column("new_value", sa.JSON, nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
        sa.Column("request_id", sa.String(255), nullable=True),
    )
    op.create_index("idx_audit_user", "audit_logs", ["user_id", "timestamp"])
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id", "timestamp"])
    op.create_index("idx_audit_action", "audit_logs", ["action", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("idx_products_category", table_name="products")
    op.drop_index("idx_products_barcode_unique", table_name="products")
    op.drop_table("products")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
