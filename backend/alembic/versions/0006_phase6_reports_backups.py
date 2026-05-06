"""Phase 6: reports/exports + backups.

Revision ID: 0006_phase6_reports_backups
Revises: 0005_phase5_reservations
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_phase6_reports_backups"
down_revision = "0005_phase5_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False, server_default="csv"),
        sa.Column("filters", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("download_url", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "backups",
        sa.Column("backup_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("backups")
    op.drop_table("export_jobs")
