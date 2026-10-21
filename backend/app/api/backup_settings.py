
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    AuthContext,
    get_current_context,
    require_admin_csrf,
)
from app.schemas.backup_settings import UpdateBackupSettingsRequest
from app.services.backup_settings_service import BackupSettingsService


router = APIRouter(
    prefix="/devices/{device_id}/backup-settings",
    tags=["backup-settings"],
)


def _serialize(setting) -> dict:
    return {
        "device_id": setting.device_id,
        "driver_key": setting.driver_key,
        "schedule_enabled": setting.schedule_enabled,
        "daily_time": (
            setting.daily_time.strftime("%H:%M")
            if setting.daily_time
            else None
        ),
        "retention_policy": setting.retention_policy,
        "next_run_at": (
            setting.next_run_at.isoformat()
            if setting.next_run_at
            else None
        ),
        "last_dispatched_at": (
            setting.last_dispatched_at.isoformat()
            if setting.last_dispatched_at
            else None
        ),
        "updated_at": (
            setting.updated_at.isoformat()
            if setting.updated_at
            else None
        ),
    }


@router.get("")
def get_backup_settings(
    device_id: int,
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.storage_repository import StorageRepository
    active_repo_id = db.scalar(select(StorageRepository.id).where(StorageRepository.is_active == True))
    if not active_repo_id:
        return {
            "data": {
                "device_id": device_id,
                "driver_key": None,
                "schedule_enabled": False,
                "daily_time": None,
                "retention_policy": "standard_31",
                "next_run_at": None,
                "last_dispatched_at": None,
                "updated_at": None,
            }
        }
    setting = BackupSettingsService(db).get(device_id)
    return {"data": _serialize(setting)}


@router.put("")
def update_backup_settings(
    device_id: int,
    payload: UpdateBackupSettingsRequest,
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.errors import AppError
    from app.models.storage_repository import StorageRepository
    active_repo_id = db.scalar(select(StorageRepository.id).where(StorageRepository.is_active == True))
    if not active_repo_id:
        raise AppError(
            status_code=503,
            code="STORAGE_DISCONNECTED",
            message="S3 storage is disconnected. Cannot configure settings without an active mounted S3 storage repository.",
        )
    setting = BackupSettingsService(db).update(
        device_id=device_id,
        driver_key=payload.driver_key,
        schedule_enabled=payload.schedule_enabled,
        daily_time=payload.daily_time,
        retention_policy=payload.retention_policy,
        updated_by=context.user.id,
    )

    from app.services.audit_log_service import AuditLogService
    from app.repositories.device_repository import DeviceRepository
    device = DeviceRepository(db).get_by_id(device_id)
    dev_name = device.hostname if device else f"#{device_id}"
    worker_label = payload.driver_key or "Unassigned"
    sched_info = f"enabled at {payload.daily_time}" if payload.schedule_enabled else "disabled"
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="INFO",
        event_type="BACKUP_SETTINGS_UPDATED",
        message=f"Backup settings updated for device '{dev_name}': Worker='{worker_label}', Schedule={sched_info}, Retention='{payload.retention_policy}'.",
        source_ip=context.source_ip,
        user_id=context.user.id,
        username=context.user.username,
        endpoint=f"/devices/{device_id}/backup-settings",
        details={
            "device_id": device_id,
            "hostname": dev_name,
            "driver_key": payload.driver_key,
            "schedule_enabled": payload.schedule_enabled,
            "daily_time": str(payload.daily_time) if payload.daily_time else None,
            "retention_policy": payload.retention_policy,
        },
    )

    return {"data": _serialize(setting)}


@router.delete("", status_code=204)
def clear_backup_settings(
    device_id: int,
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
) -> Response:
    BackupSettingsService(db).clear(
        device_id=device_id,
        updated_by=context.user.id,
    )

    from app.services.audit_log_service import AuditLogService
    from app.repositories.device_repository import DeviceRepository
    device = DeviceRepository(db).get_by_id(device_id)
    dev_name = device.hostname if device else f"#{device_id}"
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="WARNING",
        event_type="BACKUP_SETTINGS_CLEARED",
        message=f"Backup configuration cleared/reset for device '{dev_name}' by {context.user.username}.",
        source_ip=context.source_ip,
        user_id=context.user.id,
        username=context.user.username,
        endpoint=f"/devices/{device_id}/backup-settings",
        details={"device_id": device_id, "hostname": dev_name},
    )

    return Response(status_code=204)
