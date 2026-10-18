"""support pending_delete in config_objects storage_status

Revision ID: 013_config_object_pending_delete
Revises: 012_multi_repo_unique
"""

from alembic import op
import sqlalchemy as sa

revision = "013_config_object_pending_delete"
down_revision = "012_multi_repo_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_config_objects_storage_status", "config_objects", type_="check")
    op.create_check_constraint(
        "ck_config_objects_storage_status",
        "config_objects",
        "storage_status IN ('available', 'deleted', 'error', 'pending_delete')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_config_objects_storage_status", "config_objects", type_="check")
    op.create_check_constraint(
        "ck_config_objects_storage_status",
        "config_objects",
        "storage_status IN ('available', 'deleted', 'error')",
    )
