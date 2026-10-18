import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.celery_app import celery_app
from app.config import settings
from app.core.backup_lock import has_job_lease
from app.core.job_state import ACTIVE_STATES
from app.database import new_session
from app.models.backup_job import BackupJob
from app.models.backup_setting import DeviceBackupSetting
from app.models.device import Device
from app.repositories.backup_job_repository import BackupJobRepository
from app.services.backup_settings_service import BackupSettingsService

logger = logging.getLogger(__name__)


@celery_app.task(name="network_backup.dispatch_due_backups")
def dispatch_due_backups() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    dispatched = 0

    with new_session() as db:
        # 1. Stale Job Watchdog (REL-04): Auto-recover abandoned jobs across all ACTIVE_STATES
        stale_cutoff = now - timedelta(hours=1)
        stale_jobs = (
            db.query(BackupJob)
            .filter(
                BackupJob.state.in_(ACTIVE_STATES),
                func.coalesce(BackupJob.started_at, BackupJob.created_at) < stale_cutoff,
            )
            .all()
        )
        for sj in stale_jobs:
            # If the job holds an active lease/heartbeat in Redis, the worker is actively running it
            if has_job_lease(sj.id):
                continue
            logger.warning("Auto-failing stale abandoned job %s (state: %s, device: %s)", sj.id, sj.state, sj.device_id)
            sj.state = "FAILED"
            sj.failure_stage = "WATCHDOG"
            sj.failure_code = "STALE_JOB_ABANDONED"
            sj.failure_message = "Job timed out and was abandoned due to worker loss."
            sj.finished_at = now
        if stale_jobs:
            db.commit()

        # 2. Query due scheduled settings
        settings_to_run = (
            db.query(DeviceBackupSetting)
            .join(Device, Device.id == DeviceBackupSetting.device_id)
            .filter(
                Device.source_present.is_(True),
                DeviceBackupSetting.schedule_enabled.is_(True),
                DeviceBackupSetting.next_run_at <= now,
                DeviceBackupSetting.driver_key.isnot(None),
            )
            .with_for_update(skip_locked=True)
            .all()
        )

        job_repo = BackupJobRepository(db)
        settings_service = BackupSettingsService(db)

        for s in settings_to_run:
            active = job_repo.active_for_device(s.device_id)
            if active is not None:
                continue

            job = job_repo.create(
                device_id=s.device_id,
                trigger_type="scheduled",
                requested_by=None,
                driver_key=s.driver_key,
                max_attempts=settings.backup_max_attempts,
                scheduled_for=s.next_run_at,
            )
            s.last_dispatched_at = now
            if s.daily_time:
                s.next_run_at = settings_service._next_run(s.daily_time)
            db.commit()

            try:
                from app.tasks.backup_tasks import execute_backup
                execute_backup.delay(str(job.id))
                dispatched += 1
            except Exception as exc:
                logger.error("Failed to enqueue backup task for device %s (job %s): %s", s.device_id, job.id, exc)
                job.state = "FAILED"
                job.failure_stage = "ENQUEUE"
                job.failure_code = "DISPATCH_FAILED"
                job.failure_message = f"Failed to enqueue to Celery broker: {exc}"
                job.finished_at = now
                db.commit()

    return {"dispatched": dispatched}
