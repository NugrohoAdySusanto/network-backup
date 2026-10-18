"""create storage_repositories and custom_drivers tables

Revision ID: 010_storage_and_custom_drivers
Revises: 009_indexes
"""

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "010_storage_and_custom_drivers"
down_revision = "009_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create storage_repositories
    op.create_table(
        "storage_repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("bucket", sa.String(128), nullable=False),
        sa.Column("access_key", sa.String(128), nullable=False),
        sa.Column("secret_key_encrypted", sa.String(512), nullable=False),
        sa.Column("secure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_initialized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("repo_manifest", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_storage_repositories_is_active", "storage_repositories", ["is_active"])

    # 2. Create custom_drivers
    op.create_table(
        "custom_drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("vendor_hint", sa.String(128), nullable=False),
        sa.Column("model_hint", sa.String(128), nullable=False),
        sa.Column("transport", sa.String(32), nullable=False, server_default="ssh"),
        sa.Column("default_port", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("connect_timeout", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("command_timeout", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("need_enable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enable_command", sa.String(64), nullable=False, server_default="enable"),
        sa.Column("enable_prompt_pattern", sa.String(64), nullable=False, server_default="[#$]"),
        sa.Column("disable_paging_command", sa.String(128), nullable=True),
        sa.Column("paging_mode", sa.String(32), nullable=False, server_default="none"),
        sa.Column("backup_command", sa.String(255), nullable=False, server_default="show running-config"),
        sa.Column("output_extension", sa.String(16), nullable=False, server_default="txt"),
        sa.Column("strip_patterns", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("validation_min_length", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("validation_required_keyword", sa.String(64), nullable=True, server_default="hostname"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_custom_drivers_key", "custom_drivers", ["key"], unique=True)
    op.create_index("ix_custom_drivers_is_active", "custom_drivers", ["is_active"])

    # 3. Add repository_id to config_objects & snapshots
    op.add_column(
        "config_objects",
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storage_repositories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_config_objects_repository_id", "config_objects", ["repository_id"])

    op.add_column(
        "snapshots",
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storage_repositories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_snapshots_repository_id", "snapshots", ["repository_id"])


def downgrade() -> None:
    op.drop_index("ix_snapshots_repository_id", table_name="snapshots")
    op.drop_column("snapshots", "repository_id")

    op.drop_index("ix_config_objects_repository_id", table_name="config_objects")
    op.drop_column("config_objects", "repository_id")

    op.drop_index("ix_custom_drivers_is_active", table_name="custom_drivers")
    op.drop_index("ix_custom_drivers_key", table_name="custom_drivers")
    op.drop_table("custom_drivers")

    op.drop_index("ix_storage_repositories_is_active", table_name="storage_repositories")
    op.drop_table("storage_repositories")
