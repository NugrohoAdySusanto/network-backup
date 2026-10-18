from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        CheckConstraint(
            "change_status IN ('baseline', 'changed', 'no_change')",
            name="ck_snapshots_change_status",
        ),
        CheckConstraint(
            "retention_policy_at_capture IN ('standard_31', 'smart_7_4_12_3')",
            name="ck_snapshots_retention_policy",
        ),
        Index("uq_snapshots_backup_job", "backup_job_id", unique=True),
        Index("ix_snapshots_device_captured", "device_id", text("captured_at DESC")),
        Index("ix_snapshots_config_object", "config_object_id"),
        Index("ix_snapshots_retained", "is_retained"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    backup_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backup_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    config_object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("config_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_status: Mapped[str] = mapped_column(String(16), nullable=False)
    retention_policy_at_capture: Mapped[str] = mapped_column(String(32), nullable=False)
    display_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    is_retained: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    device = relationship("Device", back_populates="snapshots")
    backup_job = relationship("BackupJob", back_populates="snapshot")
    config_object = relationship("ConfigObject", back_populates="snapshots")
    storage_repository = relationship("StorageRepository", back_populates="snapshots")
    retention_marks = relationship(
        "SnapshotRetentionMark",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
