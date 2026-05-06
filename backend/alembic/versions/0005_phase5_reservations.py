"""Phase 5: reservations.

Revision ID: 0005_phase5_reservations
Revises: 0004_phase4_returns
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_phase5_reservations"
down_revision = "0004_phase4_returns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("reservation_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("expiry_timestamp", sa.DateTime, nullable=False),
        sa.Column(
            "reserve_ledger_id",
            sa.BigInteger,
            sa.ForeignKey("inventory_ledger.ledger_id"),
            nullable=True,
        ),
        sa.Column(
            "release_ledger_id",
            sa.BigInteger,
            sa.ForeignKey("inventory_ledger.ledger_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
    )
    op.create_index("idx_reservations_product", "reservations", ["product_id"])
    op.create_index("idx_reservations_status", "reservations", ["status", "expiry_timestamp"])
    op.create_index("idx_reservations_reference", "reservations", ["reference"])


def downgrade() -> None:
    op.drop_index("idx_reservations_reference", table_name="reservations")
    op.drop_index("idx_reservations_status", table_name="reservations")
    op.drop_index("idx_reservations_product", table_name="reservations")
    op.drop_table("reservations")
