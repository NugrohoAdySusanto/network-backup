
from __future__ import annotations

import uuid

from app.celery_app import celery_app
from app.database import new_session
from app.services.backup_execution_service import BackupExecutionService


@celery_app.task(name="network_backup.execute_backup")
def execute_backup(job_id: str) -> dict[str, str]:
    parsed = uuid.UUID(job_id)
    with new_session() as db:
        BackupExecutionService(db).execute_c5(parsed)
    return {
        "status": "processed",
        "job_id": job_id,
    }
