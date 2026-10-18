"""multi repository unique constraints and active repo constraint

Revision ID: 012_multi_repo_unique_constraints
Revises: 011_reconcile_schema_drift
"""

from alembic import op
import sqlalchemy as sa

revision = "012_multi_repo_unique"
down_revision = "011_reconcile_schema_drift"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update config_objects indexes to be scoped by repository_id
    op.execute("DROP INDEX IF EXISTS uq_config_object_content")
    op.execute("DROP INDEX IF EXISTS uq_config_object_s3_key")

    op.create_index(
        "uq_config_object_content",
        "config_objects",
        ["repository_id", "device_id", "content_sha256"],
        unique=True,
    )
    op.create_index(
        "uq_config_object_s3_key",
        "config_objects",
        ["repository_id", "s3_bucket", "s3_key"],
        unique=True,
    )

    # 2. Add partial unique constraint on storage_repositories for single active repository
    op.execute("DROP INDEX IF EXISTS uq_storage_repositories_single_active")
    op.create_index(
        "uq_storage_repositories_single_active",
        "storage_repositories",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_storage_repositories_single_active", table_name="storage_repositories")
    op.drop_index("uq_config_object_s3_key", table_name="config_objects")
    op.drop_index("uq_config_object_content", table_name="config_objects")

    op.create_index(
        "uq_config_object_content",
        "config_objects",
        ["device_id", "content_sha256"],
        unique=True,
    )
    op.create_index(
        "uq_config_object_s3_key",
        "config_objects",
        ["s3_bucket", "s3_key"],
        unique=True,
    )
