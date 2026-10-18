from typing import Any

from app.celery_app import celery_app
from app.database import new_session
from app.services.retention_service import RetentionService


@celery_app.task(name="network_backup.run_retention")
def run_retention(dry_run: bool = False) -> dict[str, Any]:
    with new_session() as db:
        return RetentionService(db).run_retention_policy(dry_run=dry_run)


@celery_app.task(name="network_backup.purge_pending_deleted_objects")
def purge_pending_deleted_objects(grace_period_seconds: int | None = None) -> int:
    with new_session() as db:
        return RetentionService(db).purge_pending_deleted_objects_all_repos(
            grace_period_seconds=grace_period_seconds
        )


