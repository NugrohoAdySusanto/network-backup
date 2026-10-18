from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "availability_status IN ('up', 'down', 'unknown')",
            name="ck_devices_availability_status",
        ),
        Index("uq_devices_zabbix_host_id", "zabbix_host_id", unique=True),
        Index("ix_devices_source_present", "source_present"),
        Index("ix_devices_availability_status", "availability_status"),
        Index("ix_devices_hostname", "hostname"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    zabbix_host_id: Mapped[str] = mapped_column(String(64), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    host_group: Mapped[str] = mapped_column(String(255), nullable=False)
    availability_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    availability_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    zabbix_last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_present: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    backup_settings = relationship(
        "DeviceBackupSetting",
        back_populates="device",
        uselist=False,
    )
    backup_jobs = relationship("BackupJob", back_populates="device")
    config_objects = relationship("ConfigObject", back_populates="device")
    snapshots = relationship("Snapshot", back_populates="device")
