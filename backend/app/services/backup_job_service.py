
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.core.job_state import validate_transition
from app.models.backup_job import BackupJob
from app.repositories.backup_job_repository import BackupJobRepository
from app.repositories.device_repository import DeviceRepository


class BackupJobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = BackupJobRepository(db)
        self.devices = DeviceRepository(db)

    def create_manual_job(
        self,
        *,
        device_id: int,
        requested_by: int,
    ) -> BackupJob:
        device = self.devices.get_by_id(device_id)
        if device is None:
            raise AppError(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Device not found.",
            )
        if not device.source_present:
            raise AppError(
                status_code=409,
                code="DEVICE_NOT_IN_ZABBIX_SOURCE",
                message="Device is no longer present in Zabbix source.",
            )

        setting = device.backup_settings
        if setting is None or not setting.driver_key:
            raise AppError(
                status_code=409,
                code="DRIVER_NOT_ASSIGNED",
                message="Assign a Backup Driver before running backup.",
            )

        if self.jobs.active_for_device(device_id) is not None:
            raise AppError(
                status_code=409,
                code="BACKUP_ALREADY_RUNNING",
                message="A backup job is already active for this device.",
            )

        job = self.jobs.create(
            device_id=device_id,
            trigger_type="manual",
            requested_by=requested_by,
            driver_key=setting.driver_key,
            max_attempts=settings.backup_max_attempts,
        )
        self.jobs.commit()
        self.jobs.refresh(job)
        return job

    def get(self, job_id: uuid.UUID) -> BackupJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise AppError(
                status_code=404,
                code="JOB_NOT_FOUND",
                message="Backup job not found.",
            )
        return job

    def transition(
        self,
        *,
        job: BackupJob,
        target: str,
        failure_stage: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> None:
        validate_transition(job.state, target)

        now = datetime.now(timezone.utc)
        if job.started_at is None and target != "QUEUED":
            job.started_at = now

        job.state = target
        job.failure_stage = failure_stage
        job.failure_code = failure_code
        job.failure_message = failure_message

        if target in {
            "SUCCESS_CHANGED",
            "SUCCESS_NO_CHANGE",
            "SKIPPED_DEVICE_DOWN",
            "SKIPPED_STATUS_UNKNOWN",
            "FAILED",
        }:
            job.finished_at = now
            if job.started_at:
                job.duration_ms = int(
                    (now - job.started_at).total_seconds() * 1000
                )

        self.jobs.commit()
        self.jobs.refresh(job)

    def mark_enqueue_failure(
        self,
        *,
        job: BackupJob,
        message: str,
    ) -> None:
        self.transition(
            job=job,
            target="FAILED",
            failure_stage="QUEUED",
            failure_code="QUEUE_ERROR",
            failure_message=message,
        )
        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db).send_backup_failure_alert(job.id)
        except Exception:
            pass
