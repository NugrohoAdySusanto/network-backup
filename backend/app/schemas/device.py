
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackupSettingsSummary(BaseModel):
    driver_key: str | None = None
    schedule_enabled: bool = False
    daily_time: str | None = None
    retention_policy: str = "standard_31"


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zabbix_host_id: str
    hostname: str
    ip_address: str
    vendor: str | None
    model: str | None
    host_group: str
    availability_status: str
    availability_checked_at: datetime | None
    zabbix_last_sync_at: datetime | None
    source_present: bool
    backup_settings: BackupSettingsSummary | None = None
