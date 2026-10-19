from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    category: str
    severity: str
    event_type: str
    source_ip: str | None = None
    user_agent: str | None = None
    user_id: int | None = None
    username: str | None = None
    endpoint: str | None = None
    message: str
    details: dict[str, Any] | None = None

    @computed_field
    @property
    def log_id(self) -> str:
        return f"LOG-{self.id:06d}"

    @computed_field
    @property
    def request_id(self) -> str | None:
        if self.details and isinstance(self.details, dict):
            return self.details.get("request_id")
        return None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogStatsResponse(BaseModel):
    total_logs: int
    security_incidents: int
    failed_logins: int
    system_errors: int
    category_breakdown: dict[str, int]
    severity_breakdown: dict[str, int]
