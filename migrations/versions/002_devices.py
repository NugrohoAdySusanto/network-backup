"""create devices table

Revision ID: 002_devices
Revises: 001_users
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_devices"
down_revision = "001_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("zabbix_host_id", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=False),
        sa.Column("vendor", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("host_group", sa.String(length=255), nullable=False),
        sa.Column("availability_status", sa.String(length=16), server_default="unknown", nullable=False),
        sa.Column("availability_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("zabbix_last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_present", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "availability_status IN ('up', 'down', 'unknown')",
            name="ck_devices_availability_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("devices")
