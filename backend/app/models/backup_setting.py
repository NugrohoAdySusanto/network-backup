from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceBackupSetting(Base):
    __tablename__ = "device_backup_settings"
    __table_args__ = (
        CheckConstraint(
            "retention_policy IN ('standard_31', 'smart_7_4_12_3')",
            name="ck_device_backup_settings_retention_policy",
        ),
        CheckConstraint(
            """
            daily_time IS NULL
            OR (
                (EXTRACT(MINUTE FROM daily_time)::INT % 5 = 0)
                AND EXTRACT(SECOND FROM daily_time) = 0
            )
            """,
            name="ck_device_backup_settings_five_minute_slot",
        ),
        Index(
            "uq_enabled_daily_time",
            "daily_time",
            unique=True,
            postgresql_where=text("schedule_enabled = true"),
        ),
        Index(
            "ix_device_backup_settings_next_run",
            "next_run_at",
            postgresql_where=text("schedule_enabled = true"),
        ),
    )

    device_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    driver_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    daily_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    retention_policy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="standard_31",
        server_default="standard_31",
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    device = relationship("Device", back_populates="backup_settings")
    updated_by_user = relationship(
        "User",
        back_populates="settings_updated",
        foreign_keys=[updated_by],
    )
