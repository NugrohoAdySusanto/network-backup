"""create repository_device_setting_archives table

Revision ID: 016_repo_setting_archives
Revises: 015_system_audit_logs
"""

from alembic import op
import sqlalchemy as sa

revision = "016_repo_setting_archives"
down_revision = "015_system_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_device_setting_archives",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("s3_bucket", sa.String(length=128), nullable=False),
        sa.Column("device_hostname", sa.String(length=255), nullable=False),
        sa.Column("device_zabbix_id", sa.String(length=64), nullable=True),
        sa.Column("driver_key", sa.String(length=64), nullable=True),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("daily_time", sa.Time(timezone=False), nullable=True),
        sa.Column("retention_policy", sa.String(length=32), nullable=False, server_default="standard_31"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repo_setting_archives_bucket",
        "repository_device_setting_archives",
        ["s3_bucket"],
    )
    op.create_index(
        "uq_repo_setting_archives_bucket_hostname",
        "repository_device_setting_archives",
        ["s3_bucket", "device_hostname"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_repo_setting_archives_bucket_hostname", table_name="repository_device_setting_archives")
    op.drop_index("ix_repo_setting_archives_bucket", table_name="repository_device_setting_archives")
    op.drop_table("repository_device_setting_archives")
