from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('manual', 'scheduled')",
            name="ck_backup_jobs_trigger_type",
        ),
        CheckConstraint(
            "zabbix_status_at_start IS NULL OR zabbix_status_at_start IN ('up', 'down', 'unknown')",
            name="ck_backup_jobs_zabbix_status",
        ),
        CheckConstraint(
            "change_status IS NULL OR change_status IN ('baseline', 'changed', 'no_change')",
            name="ck_backup_jobs_change_status",
        ),
        Index("ix_backup_jobs_device_created", "device_id", text("created_at DESC")),
        Index("ix_backup_jobs_state", "state"),
        Index("ix_backup_jobs_created", text("created_at DESC")),
        Index("ix_backup_jobs_scheduled_for", "scheduled_for"),
        Index(
            "ix_backup_jobs_device_success",
            "device_id",
            text("finished_at DESC"),
            postgresql_where=text(
                "state IN ('SUCCESS_CHANGED', 'SUCCESS_NO_CHANGE')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    device_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    driver_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="QUEUED",
        server_default="QUEUED",
    )
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_attempts: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        server_default="3",
    )
    zabbix_status_at_start: Mapped[str | None] = mapped_column(String(16), nullable=True)
    zabbix_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    content_sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    change_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    normalized_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    failure_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    device = relationship("Device", back_populates="backup_jobs")
    requested_by_user = relationship(
        "User",
        back_populates="backup_jobs_requested",
        foreign_keys=[requested_by],
    )
    snapshot = relationship(
        "Snapshot",
        back_populates="backup_job",
        uselist=False,
    )
