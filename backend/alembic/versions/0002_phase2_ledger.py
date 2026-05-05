"""Phase 2: inventory ledger, stock snapshot, low-stock alerts.

Revision ID: 0002_phase2_ledger
Revises: 0001_phase1_init
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_phase2_ledger"
down_revision = "0001_phase1_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_ledger",
        sa.Column("ledger_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("quantity_delta", sa.Integer, nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("destination", sa.String(100), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ledger_product", "inventory_ledger", ["product_id", "timestamp"])
    op.create_index("idx_ledger_type", "inventory_ledger", ["type", "timestamp"])
    op.create_index("idx_ledger_reference", "inventory_ledger", ["reference"])
    op.create_index("idx_ledger_user", "inventory_ledger", ["user_id", "timestamp"])

    op.create_table(
        "stock_snapshot",
        sa.Column("snapshot_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.product_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("on_hand", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reserved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("available", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "last_ledger_id",
            sa.BigInteger,
            sa.ForeignKey("inventory_ledger.ledger_id"),
            nullable=True,
        ),
        sa.Column("snapshot_timestamp", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "low_stock_alerts",
        sa.Column("alert_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("on_hand", sa.Integer, nullable=False),
        sa.Column("reorder_threshold", sa.Integer, nullable=False),
        sa.Column("alert_date", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "alert_date", name="uq_low_stock_per_day"),
    )
    op.create_index("idx_low_stock_date", "low_stock_alerts", ["alert_date"])

    # Postgres-only: enforce ledger immutability at DB level
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_ledger_mutation()
            RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'inventory_ledger is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            "CREATE TRIGGER trg_ledger_no_update BEFORE UPDATE ON inventory_ledger "
            "FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();"
        )
        op.execute(
            "CREATE TRIGGER trg_ledger_no_delete BEFORE DELETE ON inventory_ledger "
            "FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_ledger_no_update ON inventory_ledger;")
        op.execute("DROP TRIGGER IF EXISTS trg_ledger_no_delete ON inventory_ledger;")
        op.execute("DROP FUNCTION IF EXISTS reject_ledger_mutation();")
    op.drop_index("idx_low_stock_date", table_name="low_stock_alerts")
    op.drop_table("low_stock_alerts")
    op.drop_table("stock_snapshot")
    op.drop_index("idx_ledger_user", table_name="inventory_ledger")
    op.drop_index("idx_ledger_reference", table_name="inventory_ledger")
    op.drop_index("idx_ledger_type", table_name="inventory_ledger")
    op.drop_index("idx_ledger_product", table_name="inventory_ledger")
    op.drop_table("inventory_ledger")
