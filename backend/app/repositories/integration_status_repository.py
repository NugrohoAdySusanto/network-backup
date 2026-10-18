
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.integration_status import IntegrationStatus


class IntegrationStatusRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(
        self,
        *,
        name: str,
        status: str,
        summary: str | None,
        details: dict | None,
        checked_at: datetime,
        success: bool,
    ) -> IntegrationStatus:
        record = self.db.get(IntegrationStatus, name)
        if record is None:
            record = IntegrationStatus(
                name=name,
                status=status,
                summary=summary,
                details=details,
                last_checked_at=checked_at,
                last_success_at=checked_at if success else None,
            )
            self.db.add(record)
        else:
            record.status = status
            record.summary = summary
            record.details = details
            record.last_checked_at = checked_at
            if success:
                record.last_success_at = checked_at

        return record
