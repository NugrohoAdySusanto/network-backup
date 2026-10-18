from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthContext, get_current_context
from app.integrations.ceph_health_client import CephHealthClient
from app.models.backup_job import BackupJob
from app.models.backup_setting import DeviceBackupSetting
from app.models.device import Device

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    _: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    from zoneinfo import ZoneInfo
    from app.config import settings

    tz = ZoneInfo(settings.app_timezone)
    local_now = datetime.now(tz)
    local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = local_today_start.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)

    # Total active devices
    total_devices = db.query(Device).filter(Device.source_present.is_(True)).count()

    # Check active storage repository
    from app.models.storage_repository import StorageRepository
    active_repo = db.query(StorageRepository).filter(StorageRepository.is_active.is_(True)).first()
    active_repo_id = active_repo.id if active_repo else None

    # Scheduled devices (devices with schedule enabled)
    scheduled_devices_today = (
        db.query(DeviceBackupSetting)
        .join(Device, Device.id == DeviceBackupSetting.device_id)
        .filter(Device.source_present.is_(True), DeviceBackupSetting.schedule_enabled.is_(True))
        .count()
    )

    if not active_repo_id:
        successful_devices_today = 0
        target_devices_today = 0
        rate = 0.0
    else:
        # Successful backup jobs today scoped to active repository
        from sqlalchemy import or_
        from app.models.snapshot import Snapshot

        successful_devices_today = (
            db.query(BackupJob.device_id)
            .outerjoin(Snapshot, Snapshot.backup_job_id == BackupJob.id)
            .filter(
                BackupJob.state.in_(["SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"]),
                BackupJob.created_at >= today_start,
                or_(
                    BackupJob.repository_id == active_repo_id,
                    Snapshot.repository_id == active_repo_id,
                ),
            )
            .distinct()
            .count()
        )
        target_devices_today = max(scheduled_devices_today, successful_devices_today)
        rate = round((successful_devices_today / target_devices_today) * 100, 2) if target_devices_today > 0 else 0.0

    # Ceph health
    ceph_client = CephHealthClient()
    ceph_health = ceph_client.get_health()

    # Zabbix last sync time from newest device
    last_device_sync = (
        db.query(func.max(Device.zabbix_last_sync_at))
        .filter(Device.source_present.is_(True))
        .scalar()
    )
    last_zabbix_sync = (
        last_device_sync.isoformat() if last_device_sync else now.isoformat()
    )

    return {
        "data": {
            "total_devices": total_devices,
            "scheduled_devices_today": target_devices_today,
            "successful_devices_today": successful_devices_today,
            "backup_success_rate_today": rate,
            "ceph": {
                "status": ceph_health.status,
                "summary": ceph_health.summary,
                "last_checked_at": ceph_health.last_checked_at,
            },
            "zabbix": {
                "status": "OK" if total_devices > 0 else "UNKNOWN",
                "summary": f"{total_devices} network devices synchronized.",
                "last_checked_at": last_zabbix_sync,
            },
        }
    }
