
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.backup_setting import DeviceBackupSetting
from app.models.device import Device


class DeviceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, device_id: int) -> Device | None:
        stmt = (
            select(Device)
            .options(
                selectinload(Device.backup_settings),
                selectinload(Device.snapshots),
                selectinload(Device.backup_jobs),
            )
            .where(Device.id == device_id)
        )
        return self.db.scalar(stmt)

    def get_by_zabbix_host_id(self, host_id: str) -> Device | None:
        stmt = select(Device).where(Device.zabbix_host_id == host_id)
        return self.db.scalar(stmt)

    def list_devices(
        self,
        *,
        source_present: bool | None,
        status: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Device]:
        stmt = (
            select(Device)
            .options(
                selectinload(Device.backup_settings),
                selectinload(Device.snapshots),
                selectinload(Device.backup_jobs),
            )
            .order_by(Device.hostname.asc())
        )

        if source_present is not None:
            stmt = stmt.where(Device.source_present.is_(source_present))
        if status is not None:
            stmt = stmt.where(Device.availability_status == status)
        if search:
            token = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Device.hostname.ilike(token),
                    Device.vendor.ilike(token),
                    Device.model.ilike(token),
                    Device.ip_address.cast(String).ilike(token),
                )
            )

        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def count_devices(
        self,
        *,
        source_present: bool | None = None,
    ) -> int:
        stmt = select(Device.id)
        if source_present is not None:
            stmt = stmt.where(Device.source_present.is_(source_present))
        return len(list(self.db.scalars(stmt).all()))

    def upsert_from_zabbix(
        self,
        *,
        zabbix_host_id: str,
        hostname: str,
        ip_address: str,
        vendor: str | None,
        model: str | None,
        host_group: str,
        availability_status: str,
        availability_checked_at: datetime | None,
        sync_time: datetime,
    ) -> Device:
        device = self.get_by_zabbix_host_id(zabbix_host_id)

        if device is None:
            device = Device(
                zabbix_host_id=zabbix_host_id,
                hostname=hostname,
                ip_address=ip_address,
                vendor=vendor,
                model=model,
                host_group=host_group,
                availability_status=availability_status,
                availability_checked_at=availability_checked_at,
                zabbix_last_sync_at=sync_time,
                source_present=True,
            )
            self.db.add(device)
            self.db.flush()

            self.db.add(
                DeviceBackupSetting(
                    device_id=device.id,
                    schedule_enabled=False,
                    retention_policy="standard_31",
                )
            )
        else:
            device.hostname = hostname
            device.ip_address = ip_address
            device.vendor = vendor
            device.model = model
            device.host_group = host_group
            device.availability_status = availability_status
            device.availability_checked_at = availability_checked_at
            device.zabbix_last_sync_at = sync_time
            device.source_present = True

        return device

    def mark_missing_sources(
        self,
        *,
        seen_host_ids: set[str],
        sync_time: datetime,
    ) -> int:
        stmt = select(Device).where(Device.source_present.is_(True))
        changed = 0
        for device in self.db.scalars(stmt).all():
            if device.zabbix_host_id not in seen_host_ids:
                device.source_present = False
                device.availability_status = "unknown"
                device.availability_checked_at = sync_time
                changed += 1
        return changed

    def commit(self) -> None:
        self.db.commit()
