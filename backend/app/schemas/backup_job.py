
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BackupJobSummary(BaseModel):
    id: UUID
    device_id: int
    trigger_type: str
    driver_key: str | None
    state: str
    attempt_count: int
    max_attempts: int
    change_status: str | None
    zabbix_status_at_start: str | None
    failure_stage: str | None
    failure_code: str | None
    failure_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime
