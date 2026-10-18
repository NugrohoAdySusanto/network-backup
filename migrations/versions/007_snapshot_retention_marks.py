"""create snapshot retention marks

Revision ID: 007_marks
Revises: 006_snapshots
"""

from alembic import op
import sqlalchemy as sa

revision = "007_marks"
down_revision = "006_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snapshot_retention_marks",
        sa.Column("snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("mark_type", sa.String(length=32), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            """
            mark_type IN (
                'STANDARD_WINDOW',
                'DAILY',
                'WEEKLY',
                'MONTHLY',
                'YEARLY',
                'LATEST_GOOD'
            )
            """,
            name="ck_snapshot_retention_marks_type",
        ),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("snapshot_id", "mark_type"),
    )


def downgrade() -> None:
    op.drop_table("snapshot_retention_marks")
