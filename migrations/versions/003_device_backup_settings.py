"""create device backup settings

Revision ID: 003_settings
Revises: 002_devices
"""

from alembic import op
import sqlalchemy as sa

revision = "003_settings"
down_revision = "002_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_backup_settings",
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("driver_key", sa.String(length=64), nullable=True),
        sa.Column("schedule_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("daily_time", sa.Time(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_policy", sa.String(length=32), server_default="standard_31", nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "retention_policy IN ('standard_31', 'smart_7_4_12_3')",
            name="ck_device_backup_settings_retention_policy",
        ),
        sa.CheckConstraint(
            """
            daily_time IS NULL
            OR (
                (EXTRACT(MINUTE FROM daily_time)::INT % 5 = 0)
                AND EXTRACT(SECOND FROM daily_time) = 0
            )
            """,
            name="ck_device_backup_settings_five_minute_slot",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("device_id"),
    )


def downgrade() -> None:
    op.drop_table("device_backup_settings")
