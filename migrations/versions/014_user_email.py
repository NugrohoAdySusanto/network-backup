"""add email column to users table

Revision ID: 014_add_user_email
Revises: 013_config_object_pending_delete
"""

from alembic import op
import sqlalchemy as sa

revision = "014_user_email"
down_revision = "013_config_object_pending_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.create_index("uq_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_email", table_name="users")
    op.drop_column("users", "email")
