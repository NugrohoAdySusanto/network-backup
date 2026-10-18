
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.job_state import ACTIVE_STATES
from app.models.backup_job import BackupJob
from app.models.snapshot import Snapshot


class BackupJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: uuid.UUID) -> BackupJob | None:
        return self.db.get(BackupJob, job_id)

    def create(
        self,
        *,
        device_id: int,
        trigger_type: str,
        requested_by: int | None,
        driver_key: str,
        max_attempts: int,
        scheduled_for: datetime | None = None,
        repository_id: uuid.UUID | None = None,
    ) -> BackupJob:
        if repository_id is None:
            from app.models.storage_repository import StorageRepository
            repository_id = self.db.scalar(
                select(StorageRepository.id).where(StorageRepository.is_active == True)
            )
        job = BackupJob(
            device_id=device_id,
            trigger_type=trigger_type,
            requested_by=requested_by,
            driver_key=driver_key,
            scheduled_for=scheduled_for,
            repository_id=repository_id,
            state="QUEUED",
            attempt_count=0,
            max_attempts=max_attempts,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def active_for_device(self, device_id: int) -> BackupJob | None:
        stmt = (
            select(BackupJob)
            .where(
                BackupJob.device_id == device_id,
                BackupJob.state.in_(ACTIVE_STATES),
            )
            .order_by(BackupJob.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_for_device(
        self,
        *,
        device_id: int,
        state: str | None,
        trigger_type: str | None,
        limit: int,
        offset: int,
        repository_id: uuid.UUID | None = None,
        strict_repository_filter: bool = False,
    ) -> list[BackupJob]:
        stmt = (
            select(BackupJob)
            .options(
                selectinload(BackupJob.snapshot).selectinload(Snapshot.retention_marks)
            )
            .where(BackupJob.device_id == device_id)
            .order_by(BackupJob.created_at.desc())
        )
        if repository_id is not None:
            stmt = stmt.where(
                (BackupJob.repository_id == repository_id) |
                (BackupJob.snapshot.has(Snapshot.repository_id == repository_id))
            )
        elif strict_repository_filter:
            stmt = stmt.where(BackupJob.repository_id.is_(None))
        if state:
            stmt = stmt.where(BackupJob.state == state)
        if trigger_type:
            stmt = stmt.where(BackupJob.trigger_type == trigger_type)
        return list(
            self.db.scalars(
                stmt.limit(limit).offset(offset)
            ).all()
        )

    def latest_success_for_device(
        self,
        device_id: int,
    ) -> BackupJob | None:
        stmt = (
            select(BackupJob)
            .where(
                BackupJob.device_id == device_id,
                BackupJob.state.in_(
                    {"SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"}
                ),
            )
            .order_by(BackupJob.finished_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, job: BackupJob) -> None:
        self.db.refresh(job)
