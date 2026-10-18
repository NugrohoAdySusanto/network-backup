"""create system_audit_logs table

Revision ID: 015_system_audit_logs
Revises: 014_user_email
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015_system_audit_logs"
down_revision = "014_user_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_created_at",
        "system_audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_category",
        "system_audit_logs",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_severity",
        "system_audit_logs",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_event_type",
        "system_audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_source_ip",
        "system_audit_logs",
        ["source_ip"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_filter",
        "system_audit_logs",
        ["created_at", "category", "severity"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_filter", table_name="system_audit_logs")
    op.drop_index("ix_audit_logs_source_ip", table_name="system_audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="system_audit_logs")
    op.drop_index("ix_audit_logs_severity", table_name="system_audit_logs")
    op.drop_index("ix_audit_logs_category", table_name="system_audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="system_audit_logs")
    op.drop_table("system_audit_logs")
