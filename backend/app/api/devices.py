
from __future__ import annotations

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
from app.models.storage_repository import StorageRepository
from app.repositories.device_repository import DeviceRepository
from app.tasks.zabbix_tasks import sync_zabbix_devices


router = APIRouter(prefix="/devices", tags=["devices"])


def _serialize_device(
    device,
    active_repo_id: str | None = None,
    is_s3_connected: bool = True,
) -> dict:
    setting = device.backup_settings
    if not is_s3_connected:
        # When disconnected from S3/repo, snapshots are empty and settings revert to default
        device_snapshots = []
        latest_snapshot = None
        device_jobs = [
            j for j in (getattr(device, "backup_jobs", None) or [])
            if not getattr(j, "repository_id", None)
        ]
        backup_settings_data = {
            "driver_key": None,
            "schedule_enabled": False,
            "daily_time": None,
            "next_run_at": None,
            "retention_policy": "standard_31",
        }
    else:
        device_snapshots = getattr(device, "snapshots", None) or []
        if active_repo_id is not None:
            device_snapshots = [
                s for s in device_snapshots
                if str(getattr(s, "repository_id", "")) == str(active_repo_id)
            ]
        latest_snapshot = (
            max(device_snapshots, key=lambda s: s.captured_at, default=None)
            if device_snapshots
            else None
        )

        device_jobs = getattr(device, "backup_jobs", None) or []
        if active_repo_id is not None:
            device_jobs = [
                j for j in device_jobs
                if (getattr(j, "repository_id", None) and str(j.repository_id) == str(active_repo_id)) or
                   (getattr(j, "snapshot", None) and str(j.snapshot.repository_id) == str(active_repo_id))
            ]

        backup_settings_data = {
            "driver_key": setting.driver_key if setting else None,
            "schedule_enabled": (
                setting.schedule_enabled if setting else False
            ),
            "daily_time": (
                setting.daily_time.strftime("%H:%M")
                if setting and setting.daily_time
                else None
            ),
            "next_run_at": (
                setting.next_run_at.isoformat()
                if setting and setting.next_run_at
                else None
            ),
            "retention_policy": (
                setting.retention_policy
                if setting
                else "standard_31"
            ),
        }

    latest_job = (
        max(device_jobs, key=lambda j: j.created_at, default=None)
        if device_jobs
        else None
    )

    last_backup_data = None
    if latest_job:
        if latest_job.state in {"SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"}:
            status = "success"
        elif latest_job.state in {
            "FAILED",
            "SKIPPED_DEVICE_DOWN",
            "SKIPPED_STATUS_UNKNOWN",
            "SKIPPED",
        }:
            status = "failed"
        elif latest_job.state in {
            "QUEUED",
            "RUNNING",
            "CONNECTING",
            "AUTHENTICATING",
            "DISCOVERING",
            "EXTRACTING",
            "VALIDATING",
            "HASHING",
            "UPLOADING",
        }:
            status = "running"
        else:
            status = "failed" if "FAIL" in latest_job.state else "unknown"

        last_backup_data = {
            "id": latest_snapshot.id if latest_snapshot else None,
            "job_id": str(latest_job.id),
            "status": status,
            "state": latest_job.state,
            "trigger_type": latest_job.trigger_type,
            "captured_at": (
                (latest_job.finished_at or latest_job.created_at).isoformat()
            ),
            "change_status": latest_job.change_status or (
                latest_snapshot.change_status if latest_snapshot else None
            ),
            "display_filename": (
                latest_snapshot.display_filename if latest_snapshot else None
            ),
            "failure_message": latest_job.failure_message,
            "failure_code": latest_job.failure_code,
            "duration_ms": latest_job.duration_ms,
        }
    elif latest_snapshot:
        last_backup_data = {
            "id": latest_snapshot.id,
            "job_id": None,
            "status": "success",
            "state": "SUCCESS",
            "trigger_type": "manual",
            "captured_at": latest_snapshot.captured_at.isoformat(),
            "change_status": latest_snapshot.change_status,
            "display_filename": latest_snapshot.display_filename,
            "failure_message": None,
            "failure_code": None,
            "duration_ms": None,
        }
    return {
        "id": device.id,
        "zabbix_host_id": device.zabbix_host_id,
        "hostname": device.hostname,
        "ip_address": str(device.ip_address),
        "vendor": device.vendor,
        "model": device.model,
        "host_group": device.host_group,
        "availability_status": device.availability_status,
        "availability_checked_at": (
            device.availability_checked_at.isoformat()
            if device.availability_checked_at
            else None
        ),
        "zabbix_last_sync_at": (
            device.zabbix_last_sync_at.isoformat()
            if device.zabbix_last_sync_at
            else None
        ),
        "source_present": device.source_present,
        "last_backup": last_backup_data,
        "backup_settings": backup_settings_data,
    }


@router.post("/sync-zabbix", status_code=202)
def manual_sync_zabbix(
    _: AuthContext = Depends(require_admin_csrf),
):
    task = sync_zabbix_devices.delay()
    return {
        "data": {
            "task_id": task.id,
            "status": "QUEUED",
        }
    }


@router.get("")
def list_devices(
    source_present: bool | None = Query(default=True),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    if status not in {None, "up", "down", "unknown"}:
        raise AppError(
            status_code=422,
            code="INVALID_DEVICE_STATUS",
            message="Status must be up, down, or unknown.",
        )

    repository = DeviceRepository(db)
    devices = repository.list_devices(
        source_present=source_present,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = repository.count_devices(source_present=source_present)
    active_repo_id = db.scalar(select(StorageRepository.id).where(StorageRepository.is_active == True))
    is_s3_connected = active_repo_id is not None
    return {
        "data": {
            "items": [
                _serialize_device(device, active_repo_id, is_s3_connected=is_s3_connected)
                for device in devices
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/{device_id}")
def get_device(
    device_id: int,
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    device = DeviceRepository(db).get_by_id(device_id)
    if device is None:
        raise AppError(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message="Device not found.",
        )
    active_repo_id = db.scalar(select(StorageRepository.id).where(StorageRepository.is_active == True))
    is_s3_connected = active_repo_id is not None
    return {
        "data": _serialize_device(device, active_repo_id, is_s3_connected=is_s3_connected)
    }
