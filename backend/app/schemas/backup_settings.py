
from __future__ import annotations

from datetime import time

from pydantic import BaseModel


class UpdateBackupSettingsRequest(BaseModel):
    driver_key: str | None = None
    schedule_enabled: bool = False
    daily_time: time | None = None
    retention_policy: str = "standard_31"
