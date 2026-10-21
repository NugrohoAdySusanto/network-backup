import sys
from app.core.database import SessionLocal
from app.models.audit_log import SystemAuditLog
from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.storage_repository import StorageRepository

db = SessionLocal()
total_logs = db.query(SystemAuditLog).count()
total_jobs = db.query(BackupJob).count()
total_devices = db.query(Device).count()
total_repos = db.query(StorageRepository).count()

print(f"TOTAL_LOGS: {total_logs}")
print(f"TOTAL_JOBS: {total_jobs}")
print(f"TOTAL_DEVICES: {total_devices}")
print(f"TOTAL_REPOS: {total_repos}")

print("\n--- SAMPLE RECENT LOGS ---")
for l in db.query(SystemAuditLog).order_by(SystemAuditLog.created_at.desc()).limit(10).all():
    print(f"[{l.id}] {l.created_at} | {l.category} | {l.severity} | {l.event_type} | {l.message[:80]}")

print("\n--- CATEGORY BREAKDOWN ---")
from sqlalchemy import func
cats = db.query(SystemAuditLog.category, func.count(SystemAuditLog.id)).group_by(SystemAuditLog.category).all()
for cat, cnt in cats:
    print(f"Category '{cat}': {cnt} logs")

print("\n--- CHECK MISSING BACKUP JOBS IN LOGS ---")
logged_job_ids = set()
for l in db.query(SystemAuditLog).filter(SystemAuditLog.category == "BACKUP_JOB").all():
    if l.details and "job_id" in l.details:
        logged_job_ids.add(str(l.details["job_id"]))

unlogged_jobs = db.query(BackupJob).all()
missing_jobs = [j for j in unlogged_jobs if str(j.id) not in logged_job_ids]
print(f"Missing jobs not in audit logs: {len(missing_jobs)} / {len(unlogged_jobs)}")
for mj in missing_jobs[:5]:
    print(f"  Unlogged Job {mj.id}: state={mj.state}, trigger={mj.trigger_type}, created={mj.created_at}")

db.close()
