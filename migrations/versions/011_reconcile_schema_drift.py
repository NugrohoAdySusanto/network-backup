"""reconcile schema drift and indexes

Revision ID: 011_reconcile_schema_drift
Revises: 010_storage_and_custom_drivers
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011_reconcile_schema_drift"
down_revision = "010_storage_and_custom_drivers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Add master_key_encrypted to storage_repositories if not already present
    storage_repo_cols = [c["name"] for c in inspector.get_columns("storage_repositories")]
    if "master_key_encrypted" not in storage_repo_cols:
        op.add_column(
            "storage_repositories",
            sa.Column("master_key_encrypted", sa.String(512), nullable=True),
        )

    # 2. Add repository_id to backup_jobs if not already present
    backup_job_cols = [c["name"] for c in inspector.get_columns("backup_jobs")]
    if "repository_id" not in backup_job_cols:
        op.add_column(
            "backup_jobs",
            sa.Column(
                "repository_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("storage_repositories.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    # 3. Ensure indexes exist
    bj_indexes = [idx["name"] for idx in inspector.get_indexes("backup_jobs")]
    if "ix_backup_jobs_repository_id" not in bj_indexes:
        op.create_index("ix_backup_jobs_repository_id", "backup_jobs", ["repository_id"])

    sr_indexes = [idx["name"] for idx in inspector.get_indexes("storage_repositories")]
    if "ix_storage_repositories_is_active" not in sr_indexes:
        op.create_index("ix_storage_repositories_is_active", "storage_repositories", ["is_active"])

    cd_indexes = [idx["name"] for idx in inspector.get_indexes("custom_drivers")]
    if "ix_custom_drivers_is_active" not in cd_indexes:
        op.create_index("ix_custom_drivers_is_active", "custom_drivers", ["is_active"])

    co_indexes = [idx["name"] for idx in inspector.get_indexes("config_objects")]
    if "ix_config_objects_repository_id" not in co_indexes:
        op.create_index("ix_config_objects_repository_id", "config_objects", ["repository_id"])

    snap_indexes = [idx["name"] for idx in inspector.get_indexes("snapshots")]
    if "ix_snapshots_repository_id" not in snap_indexes:
        op.create_index("ix_snapshots_repository_id", "snapshots", ["repository_id"])

    # 4. Drop redundant unique constraint custom_drivers_key_key if present
    # (ix_custom_drivers_key unique index enforces uniqueness with proper indexing)
    cd_constraints = [c["name"] for c in inspector.get_unique_constraints("custom_drivers")]
    if "custom_drivers_key_key" in cd_constraints:
        op.drop_constraint("custom_drivers_key_key", "custom_drivers", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    bj_indexes = [idx["name"] for idx in inspector.get_indexes("backup_jobs")]
    if "ix_backup_jobs_repository_id" in bj_indexes:
        op.drop_index("ix_backup_jobs_repository_id", table_name="backup_jobs")

    backup_job_cols = [c["name"] for c in inspector.get_columns("backup_jobs")]
    if "repository_id" in backup_job_cols:
        op.drop_column("backup_jobs", "repository_id")

    storage_repo_cols = [c["name"] for c in inspector.get_columns("storage_repositories")]
    if "master_key_encrypted" in storage_repo_cols:
        op.drop_column("storage_repositories", "master_key_encrypted")
