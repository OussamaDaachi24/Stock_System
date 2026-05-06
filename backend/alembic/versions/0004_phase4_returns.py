"""Phase 4: returns and credit memos.

Revision ID: 0004_phase4_returns
Revises: 0003_phase3_receiving
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_phase4_returns"
down_revision = "0003_phase3_receiving"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_memos",
        sa.Column("credit_memo_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("return_id", sa.Integer, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("issued_date", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_credit_memo_return", "credit_memos", ["return_id"])
    op.create_index("idx_credit_memo_status", "credit_memos", ["status"])

    op.create_table(
        "returns",
        sa.Column("return_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("return_user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("receiving_notes", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="intake"),
        sa.Column("disposition", sa.String(50), nullable=True),
        sa.Column("disposition_notes", sa.String(1000), nullable=True),
        sa.Column("ledger_id", sa.BigInteger, sa.ForeignKey("inventory_ledger.ledger_id"), nullable=True),
        sa.Column("scrap_ledger_id", sa.BigInteger, sa.ForeignKey("inventory_ledger.ledger_id"), nullable=True),
        sa.Column("credit_memo_id", sa.Integer, sa.ForeignKey("credit_memos.credit_memo_id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_returns_product", "returns", ["product_id"])
    op.create_index("idx_returns_status", "returns", ["status"])
    op.create_index("idx_returns_reason", "returns", ["reason"])
    op.create_index("idx_returns_created", "returns", ["created_at"])

    # Deferred FK from credit_memos.return_id -> returns.return_id (skipped on
    # SQLite which doesn't enforce FKs by default; on Postgres we add it).
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_credit_memo_return",
            "credit_memos",
            "returns",
            ["return_id"],
            ["return_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_credit_memo_return", "credit_memos", type_="foreignkey")
    op.drop_index("idx_returns_created", table_name="returns")
    op.drop_index("idx_returns_reason", table_name="returns")
    op.drop_index("idx_returns_status", table_name="returns")
    op.drop_index("idx_returns_product", table_name="returns")
    op.drop_table("returns")
    op.drop_index("idx_credit_memo_status", table_name="credit_memos")
    op.drop_index("idx_credit_memo_return", table_name="credit_memos")
    op.drop_table("credit_memos")
