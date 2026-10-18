"""create snapshots

Revision ID: 006_snapshots
Revises: 005_objects
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_snapshots"
down_revision = "005_objects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("backup_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_object_id", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_status", sa.String(length=16), nullable=False),
        sa.Column("retention_policy_at_capture", sa.String(length=32), nullable=False),
        sa.Column("display_filename", sa.String(length=255), nullable=False),
        sa.Column("is_retained", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "change_status IN ('baseline', 'changed', 'no_change')",
            name="ck_snapshots_change_status",
        ),
        sa.CheckConstraint(
            "retention_policy_at_capture IN ('standard_31', 'smart_7_4_12_3')",
            name="ck_snapshots_retention_policy",
        ),
        sa.ForeignKeyConstraint(["backup_job_id"], ["backup_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["config_object_id"], ["config_objects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("snapshots")
