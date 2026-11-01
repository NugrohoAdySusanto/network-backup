
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.drivers.registry import registry
from app.models.backup_setting import DeviceBackupSetting
from app.models.storage_repository import StorageRepository
from app.repositories.backup_settings_repository import (
    BackupSettingsRepository,
)
from app.repositories.device_repository import DeviceRepository

logger = logging.getLogger(__name__)


class BackupSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.devices = DeviceRepository(db)
        self.settings = BackupSettingsRepository(db)

    def get(self, device_id: int) -> DeviceBackupSetting:
        device = self.devices.get_by_id(device_id)
        if device is None:
            raise AppError(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Device not found.",
            )
        setting = self.settings.get(device_id)
        if setting is None:
            setting = DeviceBackupSetting(
                device_id=device_id,
                schedule_enabled=False,
                retention_policy="standard_31",
            )
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        return setting

    def update(
        self,
        *,
        device_id: int,
        driver_key: str | None,
        schedule_enabled: bool,
        daily_time: time | None,
        retention_policy: str,
        updated_by: int,
    ) -> DeviceBackupSetting:
        device = self.devices.get_by_id(device_id)
        if device is None:
            raise AppError(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Device not found.",
            )

        if driver_key is not None and not registry.has(driver_key):
            raise AppError(
                status_code=422,
                code="DRIVER_KEY_INVALID",
                message="Backup Driver is not registered.",
            )

        # Normalize retention policy aliases
        if retention_policy in {"standard_31", "31", "all", "standard"}:
            retention_policy = "standard_31"
        elif retention_policy in {"smart_7_4_12_3", "smart"}:
            retention_policy = "smart_7_4_12_3"
        else:
            raise AppError(
                status_code=422,
                code="RETENTION_POLICY_INVALID",
                message="Retention policy is invalid.",
            )

        if schedule_enabled:
            if not device.source_present:
                raise AppError(
                    status_code=409,
                    code="DEVICE_NOT_IN_ZABBIX_SOURCE",
                    message="Device is no longer present in Zabbix source.",
                )
            if not driver_key:
                raise AppError(
                    status_code=409,
                    code="DRIVER_NOT_ASSIGNED",
                    message="Assign a Backup Driver before enabling schedule.",
                )
            if daily_time is None:
                raise AppError(
                    status_code=422,
                    code="SCHEDULE_TIME_REQUIRED",
                    message="Daily backup time is required.",
                )
            daily_time = daily_time.replace(second=0, microsecond=0)
            self._validate_slot(daily_time)

            owner = self.settings.slot_owner(
                daily_time=daily_time,
                exclude_device_id=device_id,
            )
            if owner is not None:
                raise AppError(
                    status_code=409,
                    code="SCHEDULE_SLOT_ALREADY_USED",
                    message="The selected daily backup slot is already used.",
                )

        setting = self.settings.get(device_id)
        if setting is None:
            setting = DeviceBackupSetting(device_id=device_id)
            self.db.add(setting)

        setting.driver_key = driver_key
        setting.schedule_enabled = schedule_enabled
        setting.daily_time = daily_time if schedule_enabled else None
        setting.retention_policy = retention_policy
        setting.updated_by = updated_by
        setting.next_run_at = (
            self._next_run(daily_time)
            if schedule_enabled and daily_time
            else None
        )

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="SCHEDULE_SLOT_ALREADY_USED",
                message="The selected daily backup slot is already used.",
            ) from exc

        self.db.refresh(setting)

        # Sync to active storage repository archive
        active_repo = self.db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
        if active_repo:
            from app.services.storage_repository_service import StorageRepositoryService
            try:
                StorageRepositoryService(self.db).save_repository_device_settings(active_repo)
            except Exception as exc:
                logger.warning("Could not sync updated device setting to repository archive: %s", exc)

        return setting

    def clear(
        self,
        *,
        device_id: int,
        updated_by: int,
    ) -> None:
        setting = self.get(device_id)
        setting.driver_key = None
        setting.schedule_enabled = False
        setting.daily_time = None
        setting.next_run_at = None
        setting.last_dispatched_at = None
        setting.updated_by = updated_by
        self.db.commit()

        # Sync to active storage repository archive
        active_repo = self.db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
        if active_repo:
            from app.services.storage_repository_service import StorageRepositoryService
            try:
                StorageRepositoryService(self.db).save_repository_device_settings(active_repo)
            except Exception as exc:
                logger.warning("Could not sync cleared device setting to repository archive: %s", exc)

    @staticmethod
    def _validate_slot(value: time) -> None:
        if (
            value.minute % settings.schedule_slot_minutes != 0
            or value.second != 0
            or value.microsecond != 0
        ):
            raise AppError(
                status_code=422,
                code="SCHEDULE_TIME_NOT_5_MINUTE_SLOT",
                message=(
                    "Daily backup time must align to a "
                    f"{settings.schedule_slot_minutes}-minute slot."
                ),
            )

    @staticmethod
    def _next_run(value: time) -> datetime:
        timezone = ZoneInfo(settings.app_timezone)
        now = datetime.now(timezone)
        candidate = datetime.combine(
            now.date(),
            value,
            tzinfo=timezone,
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
