"""create backup jobs

Revision ID: 004_jobs
Revises: 003_settings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_jobs"
down_revision = "003_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.BigInteger(), nullable=True),
        sa.Column("driver_key", sa.String(length=64), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=40), server_default="QUEUED", nullable=False),
        sa.Column("attempt_count", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.SmallInteger(), server_default="3", nullable=False),
        sa.Column("zabbix_status_at_start", sa.String(length=16), nullable=True),
        sa.Column("zabbix_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_sha256", sa.CHAR(length=64), nullable=True),
        sa.Column("change_status", sa.String(length=16), nullable=True),
        sa.Column("raw_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("normalized_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("failure_stage", sa.String(length=40), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'scheduled')",
            name="ck_backup_jobs_trigger_type",
        ),
        sa.CheckConstraint(
            "zabbix_status_at_start IS NULL OR zabbix_status_at_start IN ('up', 'down', 'unknown')",
            name="ck_backup_jobs_zabbix_status",
        ),
        sa.CheckConstraint(
            "change_status IS NULL OR change_status IN ('baseline', 'changed', 'no_change')",
            name="ck_backup_jobs_change_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("backup_jobs")
