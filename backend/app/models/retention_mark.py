from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SnapshotRetentionMark(Base):
    __tablename__ = "snapshot_retention_marks"
    __table_args__ = (
        CheckConstraint(
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
        Index("ix_retention_marks_type", "mark_type"),
    )

    snapshot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mark_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    snapshot = relationship("Snapshot", back_populates="retention_marks")

    @property
    def tier(self) -> str:
        return self.mark_type

    @property
    def retention_mark(self) -> str:
        return self.mark_type
