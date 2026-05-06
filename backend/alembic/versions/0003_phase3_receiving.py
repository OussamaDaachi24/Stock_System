"""Phase 3: suppliers, purchase orders, receipts, put-away tasks.

Revision ID: 0003_phase3_receiving
Revises: 0002_phase2_ledger
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_phase3_receiving"
down_revision = "0002_phase2_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("supplier_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("payment_terms", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("active", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_suppliers_name", "suppliers", ["name"])

    op.create_table(
        "purchase_orders",
        sa.Column("po_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.supplier_id"), nullable=False),
        sa.Column("po_number", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("expected_delivery_date", sa.DateTime, nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.user_id"), nullable=True),
    )
    op.create_index("idx_po_supplier", "purchase_orders", ["supplier_id"])
    op.create_index("idx_po_status", "purchase_orders", ["status"])

    op.create_table(
        "po_lines",
        sa.Column("po_line_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("po_id", sa.Integer, sa.ForeignKey("purchase_orders.po_id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("received_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_po_line_po", "po_lines", ["po_id"])
    op.create_index("idx_po_line_product", "po_lines", ["product_id"])

    op.create_table(
        "receipts",
        sa.Column("receipt_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("po_id", sa.Integer, sa.ForeignKey("purchase_orders.po_id"), nullable=True),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("suppliers.supplier_id"), nullable=True),
        sa.Column("receiving_user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("packing_info", sa.JSON, nullable=True),
        sa.Column("discrepancies", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_receipts_po", "receipts", ["po_id"])
    op.create_index("idx_receipts_status", "receipts", ["status"])

    op.create_table(
        "receipt_lines",
        sa.Column("receipt_line_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("receipt_id", sa.Integer, sa.ForeignKey("receipts.receipt_id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("po_line_id", sa.Integer, sa.ForeignKey("po_lines.po_line_id"), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("lot_batch", sa.String(100), nullable=True),
        sa.Column("serial_numbers", sa.JSON, nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("ledger_id", sa.BigInteger, sa.ForeignKey("inventory_ledger.ledger_id"), nullable=True),
        sa.Column("flagged", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_receipt_line_receipt", "receipt_lines", ["receipt_id"])
    op.create_index("idx_receipt_line_product", "receipt_lines", ["product_id"])

    op.create_table(
        "put_away_tasks",
        sa.Column("task_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("receipt_line_id", sa.Integer, sa.ForeignKey("receipt_lines.receipt_line_id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("from_location", sa.String(100), nullable=False, server_default="receiving"),
        sa.Column("to_location", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_putaway_status", "put_away_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("idx_putaway_status", table_name="put_away_tasks")
    op.drop_table("put_away_tasks")
    op.drop_index("idx_receipt_line_product", table_name="receipt_lines")
    op.drop_index("idx_receipt_line_receipt", table_name="receipt_lines")
    op.drop_table("receipt_lines")
    op.drop_index("idx_receipts_status", table_name="receipts")
    op.drop_index("idx_receipts_po", table_name="receipts")
    op.drop_table("receipts")
    op.drop_index("idx_po_line_product", table_name="po_lines")
    op.drop_index("idx_po_line_po", table_name="po_lines")
    op.drop_table("po_lines")
    op.drop_index("idx_po_status", table_name="purchase_orders")
    op.drop_index("idx_po_supplier", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_index("idx_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
