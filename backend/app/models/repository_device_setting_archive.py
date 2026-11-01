from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RepositoryDeviceSettingArchive(Base):
    __tablename__ = "repository_device_setting_archives"
    __table_args__ = (
        Index("ix_repo_setting_archives_bucket", "s3_bucket"),
        Index("uq_repo_setting_archives_bucket_hostname", "s3_bucket", "device_hostname", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    s3_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    device_hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    device_zabbix_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    driver_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    daily_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    retention_policy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="standard_31",
        server_default="standard_31",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

