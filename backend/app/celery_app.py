from celery import Celery
from celery.schedules import crontab

from app.config import settings


celery_app = Celery(
    "network_backup",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.scheduler_tasks",
        "app.tasks.zabbix_tasks",
        "app.tasks.health_tasks",
        "app.tasks.retention_tasks",
        "app.tasks.backup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.app_timezone,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "dispatch-due-backups": {
            "task": "network_backup.dispatch_due_backups",
            "schedule": settings.schedule_dispatch_interval_seconds,
        },
        "sync-zabbix-devices": {
            "task": "network_backup.sync_zabbix_devices",
            "schedule": settings.zabbix_sync_interval_seconds,
        },
        "refresh-ceph-health": {
            "task": "network_backup.refresh_ceph_health",
            "schedule": settings.ceph_health_interval_seconds,
        },
        "run-retention-policy": {
            "task": "network_backup.run_retention",
            "schedule": crontab(hour=settings.retention_run_hour, minute=0),
        },
        "purge-pending-deleted-objects": {
            "task": "network_backup.purge_pending_deleted_objects",
            "schedule": 3600,
        },
    },
)


from celery.signals import worker_init


@worker_init.connect
def on_worker_init(**kwargs):
    if settings.app_env != "test":
        from app.main import verify_security_configuration

        verify_security_configuration()


