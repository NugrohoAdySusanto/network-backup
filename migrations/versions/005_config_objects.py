"""create config objects

Revision ID: 005_objects
Revises: 004_jobs
"""

from alembic import op
import sqlalchemy as sa

revision = "005_objects"
down_revision = "004_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_objects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("content_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("object_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("s3_bucket", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("storage_status", sa.String(length=16), server_default="available", nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "storage_status IN ('available', 'deleted', 'error')",
            name="ck_config_objects_storage_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("config_objects")
