from __future__ import annotations

import logging
from app.database import get_db_context
from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.user import User
from app.models.storage_repository import StorageRepository
from app.models.audit_log import SystemAuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill")

def run_backfill():
    with get_db_context() as db:
        # 1. Backfill users registration
        users = db.query(User).all()
        user_count = 0
        for u in users:
            exists = db.query(SystemAuditLog).filter(
                SystemAuditLog.event_type == "USER_REGISTERED",
                SystemAuditLog.user_id == u.id
            ).first()
            if not exists:
                log = SystemAuditLog(
                    category="AUDIT",
                    severity="INFO",
                    event_type="USER_REGISTERED",
                    message=f"Akun pengguna '{u.username}' terdaftar dengan peran '{u.role}'.",
                    user_id=u.id,
                    username=u.username,
                    endpoint="POST /api/v1/users",
                    details={"user_id": u.id, "role": u.role, "email": u.email},
                    created_at=u.created_at
                )
                db.add(log)
                user_count += 1

            if u.last_login_at:
                exists_login = db.query(SystemAuditLog).filter(
                    SystemAuditLog.event_type == "LOGIN_SUCCESS",
                    SystemAuditLog.user_id == u.id,
                    SystemAuditLog.created_at == u.last_login_at
                ).first()
                if not exists_login:
                    login_log = SystemAuditLog(
                        category="AUDIT",
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
                    user_count += 1

        # 2. Backfill storage repos
        repos = db.query(StorageRepository).all()
        repo_count = 0
        for r in repos:
            exists = db.query(SystemAuditLog).filter(
                SystemAuditLog.event_type == "STORAGE_REPOSITORY_INITIALIZED",
                SystemAuditLog.message.like(f"%{r.bucket}%")
            ).first()
            if not exists:
                log = SystemAuditLog(
                    category="AUDIT",
                    severity="INFO",
                    event_type="STORAGE_REPOSITORY_INITIALIZED",
                    message=f"Repositori S3 '{r.name}' (bucket: {r.bucket}) terdaftar.",
                    endpoint="POST /api/v1/storage/initialize",
                    details={"repository_id": str(r.id), "bucket": r.bucket, "is_active": r.is_active},
                    created_at=r.created_at
                )
                db.add(log)
                repo_count += 1

        # 3. Backfill backup jobs
        jobs = db.query(BackupJob).order_by(BackupJob.created_at.asc()).all()
        job_count = 0
        for j in jobs:
            # Check if already migrated
            exists = db.query(SystemAuditLog).filter(
                SystemAuditLog.details["job_id"].astext == str(j.id)
            ).first()
            if not exists:
                is_success = j.state in ["SUCCESS_CHANGED", "SUCCESS_NO_CHANGE"]
                sev = "INFO" if is_success else "ERROR"
                evt = "BACKUP_JOB_COMPLETED" if is_success else "BACKUP_JOB_FAILED"
                dev = db.query(Device).filter(Device.id == j.device_id).first()
                dev_name = dev.hostname if dev else f"Device #{j.device_id}"
                dev_ip = str(dev.ip_address) if dev else "-"
                u = db.query(User).filter(User.id == j.requested_by).first() if j.requested_by else None
                uname = u.username if u else ("Scheduler" if j.trigger_type == "scheduled" else "System")

                if is_success:
                    msg = f"Pekerjaan backup {j.trigger_type} untuk perangkat '{dev_name}' ({dev_ip}) berhasil ({j.state}, {j.change_status or 'baseline'})."
                else:
                    fail_reason = j.failure_message or j.failure_code or j.state
                    msg = f"Pekerjaan backup {j.trigger_type} untuk perangkat '{dev_name}' ({dev_ip}) gagal: {fail_reason}"

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
                job_count += 1

        db.commit()
        print(f"Backfill complete! Added: {user_count} user logs, {repo_count} repo logs, {job_count} backup job logs.")

if __name__ == "__main__":
    run_backfill()
