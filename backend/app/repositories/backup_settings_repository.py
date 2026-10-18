
from __future__ import annotations

from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.backup_setting import DeviceBackupSetting


class BackupSettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, device_id: int) -> DeviceBackupSetting | None:
        return self.db.get(DeviceBackupSetting, device_id)

    def slot_owner(
        self,
        *,
        daily_time: time,
        exclude_device_id: int,
    ) -> DeviceBackupSetting | None:
        stmt = select(DeviceBackupSetting).where(
            DeviceBackupSetting.schedule_enabled.is_(True),
            DeviceBackupSetting.daily_time == daily_time,
            DeviceBackupSetting.device_id != exclude_device_id,
        )
        return self.db.scalar(stmt)
