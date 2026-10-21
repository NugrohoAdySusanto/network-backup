from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.backup_setting import DeviceBackupSetting
from app.models.user import User
from app.models.storage_repository import StorageRepository
from app.models.audit_log import SystemAuditLog
from app.database import get_db_context

logger = logging.getLogger("backfill")


def run_backfill_with_session(db: Session) -> dict[str, int]:
    counts = {"users": 0, "storage": 0, "jobs": 0, "settings": 0, "updated": 0}

    # 0. Migrate any existing STORAGE events from AUDIT to STORAGE category
    existing_storage_logs = db.query(SystemAuditLog).filter(
        SystemAuditLog.event_type.like("STORAGE_%")
    ).all()
    for l in existing_storage_logs:
        if l.category != "STORAGE":
            l.category = "STORAGE"
            counts["updated"] += 1

    existing_auth_logs = db.query(SystemAuditLog).filter(
        SystemAuditLog.event_type.in_(["LOGIN_SUCCESS", "LOGIN_FAILED", "USER_LOGOUT"])
    ).all()
    for l in existing_auth_logs:
        if l.category != "AUTH":
            l.category = "AUTH"
            counts["updated"] += 1

    # 1. Backfill users registration & logins
    users = db.query(User).all()
    for u in users:
        exists = db.query(SystemAuditLog).filter(
            SystemAuditLog.event_type == "USER_REGISTERED",
            SystemAuditLog.user_id == u.id
        ).first()
        if not exists:
            log = SystemAuditLog(
                category="AUTH",
                severity="INFO",
                event_type="USER_REGISTERED",
                message=f"User account '{u.username}' registered with role '{u.role}'.",
                user_id=u.id,
                username=u.username,
                endpoint="POST /api/v1/users",
                details={"user_id": u.id, "role": u.role, "email": u.email},
                created_at=u.created_at
            )
            db.add(log)
            counts["users"] += 1

        if u.last_login_at:
            exists_login = db.query(SystemAuditLog).filter(
                SystemAuditLog.event_type == "LOGIN_SUCCESS",
                SystemAuditLog.user_id == u.id,
                SystemAuditLog.created_at == u.last_login_at
            ).first()
            if not exists_login:
                login_log = SystemAuditLog(
                    category="AUTH",
                    severity="INFO",
                    event_type="LOGIN_SUCCESS",
                    message=f"User '{u.username}' logged in successfully.",
                    user_id=u.id,
                    username=u.username,
                    endpoint="POST /api/v1/auth/login",
                    details={"role": u.role, "historical": True},
                    created_at=u.last_login_at
                )
                db.add(login_log)
                counts["users"] += 1

    # 2. Backfill storage repos (Category: STORAGE)
    repos = db.query(StorageRepository).all()
    for r in repos:
        exists_init = db.query(SystemAuditLog).filter(
            SystemAuditLog.event_type == "STORAGE_REPOSITORY_INITIALIZED",
            SystemAuditLog.message.like(f"%{r.bucket}%")
        ).first()
        if not exists_init:
            log = SystemAuditLog(
                category="STORAGE",
                severity="INFO",
                event_type="STORAGE_REPOSITORY_INITIALIZED",
                message=f"S3 repository '{r.name}' (bucket: {r.bucket}) registered and initialized.",
                endpoint="POST /api/v1/storage/repositories/init",
                details={"repository_id": str(r.id), "bucket": r.bucket, "name": r.name, "is_active": r.is_active},
                created_at=r.created_at
            )
            db.add(log)
            counts["storage"] += 1

        if r.is_active:
            exists_mount = db.query(SystemAuditLog).filter(
                SystemAuditLog.event_type == "STORAGE_MOUNTED",
                SystemAuditLog.message.like(f"%{r.name}%")
            ).first()
            if not exists_mount:
                log_mount = SystemAuditLog(
                    category="STORAGE",
                    severity="INFO",
                    event_type="STORAGE_MOUNTED",
                    message=f"S3 storage repository '{r.name}' activated and mounted.",
                    endpoint=f"POST /api/v1/storage/repositories/{r.id}/activate",
                    details={"repository_id": str(r.id), "name": r.name, "bucket": r.bucket},
                    created_at=r.created_at
                )
                db.add(log_mount)
                counts["storage"] += 1

    # 3. Backfill backup jobs
    existing_job_logs = db.query(SystemAuditLog).filter(SystemAuditLog.category == "BACKUP_JOB").all()
    existing_job_ids = set()
    for ej in existing_job_logs:
        if ej.details and isinstance(ej.details, dict) and "job_id" in ej.details:
            existing_job_ids.add(str(ej.details["job_id"]))

    jobs = db.query(BackupJob).order_by(BackupJob.created_at.asc()).all()
    devices_map = {d.id: d for d in db.query(Device).all()}
    users_map = {u.id: u for u in users}

    for j in jobs:
        if str(j.id) in existing_job_ids:
            continue

        dev = devices_map.get(j.device_id)
        dev_name = dev.hostname if dev else f"Device #{j.device_id}"
        dev_ip = str(dev.ip_address).split("/")[0] if dev and dev.ip_address else "-"
        u = users_map.get(j.requested_by) if j.requested_by else None
        uname = u.username if u else ("Scheduler" if j.trigger_type == "scheduled" else "System")

        if j.failure_code == "DRIVER_NOT_ASSIGNED":
            sev = "WARNING"
            evt = "DRIVER_NOT_ASSIGNED"
            msg = f"{j.trigger_type.capitalize()} backup for device '{dev_name}' ({dev_ip}) rejected: DRIVER_NOT_ASSIGNED (Assign a Backup Worker before running backup)."
        elif j.failure_code == "STORAGE_DISCONNECTED":
            sev = "ERROR"
            evt = "STORAGE_DISCONNECTED"
            msg = f"{j.trigger_type.capitalize()} backup for device '{dev_name}' ({dev_ip}) rejected: S3 storage is disconnected."
        elif j.state in ["SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"]:
            sev = "INFO"
            evt = "BACKUP_JOB_COMPLETED"
            msg = f"{j.trigger_type.capitalize()} backup job for device '{dev_name}' ({dev_ip}) succeeded ({j.state}, {j.change_status or 'baseline'})."
        else:
            sev = "ERROR"
            evt = "BACKUP_JOB_FAILED"
            fail_reason = j.failure_message or j.failure_code or j.state
            msg = f"{j.trigger_type.capitalize()} backup job for device '{dev_name}' ({dev_ip}) failed: {fail_reason}"

        log = SystemAuditLog(
            category="BACKUP_JOB",
            severity=sev,
            event_type=evt,
            message=msg,
            user_id=j.requested_by,
            username=uname,
            endpoint="POST /api/v1/backups/manual" if j.trigger_type == "manual" else "Celery Worker Task",
            details={
                "job_id": str(j.id),
                "device_id": j.device_id,
                "hostname": dev_name,
                "ip_address": dev_ip,
                "state": j.state,
                "change_status": j.change_status,
                "driver_key": j.driver_key,
                "duration_ms": j.duration_ms,
                "failure_stage": j.failure_stage,
                "failure_code": j.failure_code,
                "failure_message": j.failure_message
            },
            created_at=j.created_at
        )
        db.add(log)
        existing_job_ids.add(str(j.id))
        counts["jobs"] += 1

    # 4. Backfill device settings (if configured)
    settings_records = db.query(DeviceBackupSetting).all()
    for s in settings_records:
        if s.driver_key or s.schedule_enabled:
            dev = devices_map.get(s.device_id)
            dev_name = dev.hostname if dev else f"Device #{s.device_id}"
            exists_s = db.query(SystemAuditLog).filter(
                SystemAuditLog.event_type == "BACKUP_SETTINGS_UPDATED",
                SystemAuditLog.message.like(f"%'{dev_name}'%")
            ).first()
            if not exists_s:
                sched_str = f"enabled at {s.daily_time.strftime('%H:%M')}" if s.schedule_enabled and s.daily_time else "disabled"
                log_s = SystemAuditLog(
                    category="AUDIT",
                    severity="INFO",
                    event_type="BACKUP_SETTINGS_UPDATED",
                    message=f"Backup settings configured for device '{dev_name}': Worker='{s.driver_key or 'None'}', Schedule={sched_str}, Retention='{s.retention_policy}'.",
                    endpoint=f"/devices/{s.device_id}/backup-settings",
                    details={
                        "device_id": s.device_id,
                        "hostname": dev_name,
                        "driver_key": s.driver_key,
                        "schedule_enabled": s.schedule_enabled,
                        "daily_time": s.daily_time.strftime("%H:%M") if s.daily_time else None,
                        "retention_policy": s.retention_policy,
                    },
                    created_at=s.updated_at if hasattr(s, "updated_at") and s.updated_at else dev.created_at if dev and hasattr(dev, "created_at") else None
                )
                db.add(log_s)
                counts["settings"] += 1

    db.commit()
    return counts


def run_backfill():
    with get_db_context() as db:
        res = run_backfill_with_session(db)
        print(f"Backfill complete! Added: {res['users']} users, {res['storage']} storage, {res['jobs']} jobs, {res['settings']} settings. Updated {res['updated']} categories.")


if __name__ == "__main__":
    run_backfill()
