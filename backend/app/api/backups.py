
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database import get_db
from app.dependencies import (
    AuthContext,
    get_current_context,
    require_admin_csrf,
)
from app.repositories.backup_job_repository import BackupJobRepository
from app.repositories.device_repository import DeviceRepository
from app.services.backup_job_service import BackupJobService
from app.tasks.backup_tasks import execute_backup


router = APIRouter(tags=["backup-jobs"])


def _serialize(job) -> dict:
    return {
        "id": str(job.id),
        "device_id": job.device_id,
        "trigger_type": job.trigger_type,
        "driver_key": job.driver_key,
        "state": job.state,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "zabbix_status_at_start": job.zabbix_status_at_start,
        "zabbix_checked_at": (
            job.zabbix_checked_at.isoformat()
            if job.zabbix_checked_at
            else None
        ),
        "content_sha256": job.content_sha256,
        "change_status": job.change_status,
        "raw_size_bytes": job.raw_size_bytes,
        "normalized_size_bytes": job.normalized_size_bytes,
        "failure": (
            {
                "stage": job.failure_stage,
                "code": job.failure_code,
                "message": job.failure_message,
            }
            if job.failure_code or job.failure_message
            else None
        ),
        "scheduled_for": (
            job.scheduled_for.isoformat()
            if job.scheduled_for
            else None
        ),
        "started_at": (
            job.started_at.isoformat()
            if job.started_at
            else None
        ),
        "finished_at": (
            job.finished_at.isoformat()
            if job.finished_at
            else None
        ),
        "duration_ms": job.duration_ms,
        "created_at": job.created_at.isoformat(),
        "snapshot": (
            {
                "id": job.snapshot.id,
                "display_filename": job.snapshot.display_filename,
                "retention_policy": job.snapshot.retention_policy_at_capture,
                "is_retained": job.snapshot.is_retained,
                "retention_marks": [
                    getattr(mark, "mark_type", getattr(mark, "tier", getattr(mark, "retention_mark", str(mark))))
                    for mark in job.snapshot.retention_marks
                ] if job.snapshot.retention_marks else [],
            }
            if hasattr(job, "snapshot") and job.snapshot
            else None
        ),
    }


@router.post("/devices/{device_id}/backup", status_code=202)
def backup_now(
    device_id: int,
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
):
    device = DeviceRepository(db).get_by_id(device_id)
    if device is None:
        raise AppError(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message="Device not found.",
        )

    from datetime import datetime, timedelta, timezone
    from app.models.backup_job import BackupJob
    from app.models.storage_repository import StorageRepository

    active_repo = db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
    from app.services.audit_log_service import AuditLogService

    if not active_repo:
        now = datetime.now(timezone.utc)
        driver_key = device.backup_settings.driver_key if device.backup_settings else None
        failed_job = BackupJob(
            device_id=device_id,
            trigger_type="manual",
            driver_key=driver_key or "unassigned",
            state="FAILED",
            failure_stage="CONNECTING",
            failure_code="STORAGE_DISCONNECTED",
            failure_message="S3 storage is disconnected. Cannot run backup without an active mounted S3 storage repository.",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            requested_by=context.user.id,
            repository_id=None,
        )
        db.add(failed_job)
        db.commit()

        AuditLogService.record_event_standalone(
            category="BACKUP_JOB",
            severity="ERROR",
            event_type="STORAGE_DISCONNECTED",
            message=f"Manual backup for device '{device.hostname}' ({device.ip_address}) rejected at CONNECTING: S3 storage is disconnected.",
            source_ip=context.source_ip,
            user_id=context.user.id,
            username=context.user.username,
            endpoint=f"/devices/{device_id}/backup",
            details={
                "device_id": device_id,
                "hostname": device.hostname,
                "failure_stage": "CONNECTING",
                "failure_code": "STORAGE_DISCONNECTED",
                "job_id": str(failed_job.id),
            },
        )
        raise AppError(
            status_code=503,
            code="STORAGE_DISCONNECTED",
            message="S3 storage is disconnected. Cannot run backup without an active mounted S3 storage repository.",
        )

    setting = device.backup_settings
    if setting is None or not setting.driver_key:
        now = datetime.now(timezone.utc)
        failed_job = BackupJob(
            device_id=device_id,
            trigger_type="manual",
            driver_key="unassigned",
            state="FAILED",
            failure_stage="CONNECTING",
            failure_code="DRIVER_NOT_ASSIGNED",
            failure_message="Assign a Backup Worker before running backup.",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            requested_by=context.user.id,
            repository_id=active_repo.id,
        )
        db.add(failed_job)
        db.commit()

        AuditLogService.record_event_standalone(
            category="BACKUP_JOB",
            severity="WARNING",
            event_type="DRIVER_NOT_ASSIGNED",
            message=f"Manual backup for device '{device.hostname}' ({device.ip_address}) rejected at CONNECTING: DRIVER_NOT_ASSIGNED (Assign a Backup Worker before running backup).",
            source_ip=context.source_ip,
            user_id=context.user.id,
            username=context.user.username,
            endpoint=f"/devices/{device_id}/backup",
            details={
                "device_id": device_id,
                "hostname": device.hostname,
                "ip_address": str(device.ip_address),
                "failure_stage": "CONNECTING",
                "failure_code": "DRIVER_NOT_ASSIGNED",
                "failure_message": "Assign a Backup Worker before running backup.",
                "job_id": str(failed_job.id),
            },
        )
        raise AppError(
            status_code=409,
            code="DRIVER_NOT_ASSIGNED",
            message="Assign a Backup Driver before running backup.",
        )

    service = BackupJobService(db)
    job = service.create_manual_job(
        device_id=device_id,
        requested_by=context.user.id,
    )

    try:
        task = execute_backup.delay(str(job.id))
        job.celery_task_id = task.id
        db.commit()
        db.refresh(job)

        AuditLogService.record_event_standalone(
            category="BACKUP_JOB",
            severity="INFO",
            event_type="BACKUP_TRIGGERED",
            message=f"Running Backup Now for device '{device.hostname}' ({device.ip_address}) [Worker: {setting.driver_key}].",
            source_ip=context.source_ip,
            user_id=context.user.id,
            username=context.user.username,
            endpoint=f"/devices/{device_id}/backup",
            details={
                "job_id": str(job.id),
                "device_id": device_id,
                "hostname": device.hostname,
                "ip_address": str(device.ip_address),
                "driver_key": setting.driver_key,
                "trigger_type": "manual",
                "celery_task_id": task.id,
            },
        )
    except Exception as exc:
        service.mark_enqueue_failure(
            job=job,
            message="Unable to enqueue backup job.",
        )
        AuditLogService.record_event_standalone(
            category="BACKUP_JOB",
            severity="ERROR",
            event_type="QUEUE_UNAVAILABLE",
            message=f"Error when running Backup Now for device '{device.hostname}': Unable to enqueue backup task.",
            source_ip=context.source_ip,
            user_id=context.user.id,
            username=context.user.username,
            endpoint=f"/devices/{device_id}/backup",
            details={
                "job_id": str(job.id),
                "device_id": device_id,
                "hostname": device.hostname,
                "error": str(exc),
            },
        )
        raise AppError(
            status_code=503,
            code="QUEUE_UNAVAILABLE",
            message="Unable to enqueue backup job.",
        ) from exc

    return {"data": _serialize(job)}


@router.get("/backup-jobs/{job_id}")
def get_backup_job(
    job_id: uuid.UUID,
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = BackupJobService(db).get(job_id)
    return {"data": _serialize(job)}


@router.get("/devices/{device_id}/backup-jobs")
def list_backup_jobs(
    device_id: int,
    state: str | None = Query(default=None),
    trigger_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    if DeviceRepository(db).get_by_id(device_id) is None:
        raise AppError(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message="Device not found.",
        )

    if trigger_type not in {None, "manual", "scheduled"}:
        raise AppError(
            status_code=422,
            code="INVALID_TRIGGER_TYPE",
            message="Trigger type must be manual or scheduled.",
        )

    from sqlalchemy import select
    from app.models.storage_repository import StorageRepository

    active_repo_id = db.scalar(
        select(StorageRepository.id).where(StorageRepository.is_active == True)
    )

    jobs = BackupJobRepository(db).list_for_device(
        device_id=device_id,
        state=state,
        trigger_type=trigger_type,
        limit=limit,
        offset=offset,
        repository_id=active_repo_id,
        strict_repository_filter=True,
    )
    return {
        "data": {
            "items": [_serialize(job) for job in jobs],
            "total": len(jobs),
            "limit": limit,
            "offset": offset,
        }
    }
