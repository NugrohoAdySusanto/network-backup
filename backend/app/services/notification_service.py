from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.feishu_client import FeishuClient
from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.integration_status import IntegrationStatus
from app.models.snapshot import Snapshot

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification orchestration service.
    Coordinates failure data assembly and dispatches alerts via integration clients
    while updating application integration status.
    """

    def __init__(self, db: Session, client: FeishuClient | None = None) -> None:
        self.db = db
        self.client = client or FeishuClient()

    def send_backup_failure_alert(self, job_id: uuid.UUID) -> dict[str, Any]:
        """
        Gathers context for a failed or skipped backup job and dispatches a Feishu alert.
        Also records the delivery outcome into the integration_status table.
        """
        job = self.db.scalar(select(BackupJob).where(BackupJob.id == job_id))
        if job is None:
            logger.error("Cannot send Feishu alert: BackupJob %s not found.", job_id)
            return {"success": False, "error": f"Job {job_id} not found"}

        device = self.db.scalar(select(Device).where(Device.id == job.device_id))
        device_name = device.hostname if device else f"Device #{job.device_id}"
        vendor = (device.vendor if device and device.vendor else "Unknown").strip()
        model = (device.model if device and device.model else "Unknown").strip()
        ip_addr = str(device.ip_address).split("/")[0] if device and device.ip_address else "Unknown"

        # Lookup last successful snapshot for this device
        last_snapshot = self.db.scalar(
            select(Snapshot)
            .where(
                Snapshot.device_id == job.device_id,
                Snapshot.is_retained == True,
            )
            .order_by(Snapshot.captured_at.desc())
            .limit(1)
        )
        last_success_time = last_snapshot.captured_at if last_snapshot else None

        result = self.client.send_backup_failure_alert(
            device_name=device_name,
            vendor=vendor,
            model=model,
            ip_address=ip_addr,
            driver_key=job.driver_key,
            job_id=str(job.id),
            occurred_at=job.finished_at or datetime.now(timezone.utc),
            final_state=job.state,
            failure_stage=job.failure_stage or "UNKNOWN",
            failure_reason=job.failure_message or job.failure_code or "Unknown error",
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            last_successful_backup=last_success_time,
        )

        now = datetime.now(timezone.utc)
        self._record_integration_status(result=result, device_name=device_name, now=now)
        return result


    def _record_integration_status(
        self,
        *,
        result: dict[str, Any],
        device_name: str,
        now: datetime,
    ) -> None:
        try:
            status_row = self.db.scalar(
                select(IntegrationStatus).where(IntegrationStatus.name == "feishu_webhook")
            )
            is_success = result.get("success", False)

            if status_row is None:
                status_row = IntegrationStatus(
                    name="feishu_webhook",
                    status="OK" if is_success else "ERROR",
                    summary=(
                        f"Alert delivered for {device_name}"
                        if is_success
                        else f"Failed to deliver alert: {result.get('error', 'unknown')}"
                    ),
                    details=result,
                    last_checked_at=now,
                    last_success_at=now if is_success else None,
                )
                self.db.add(status_row)
            else:
                status_row.status = "OK" if is_success else "ERROR"
                status_row.summary = (
                    f"Alert delivered for {device_name}"
                    if is_success
                    else f"Failed to deliver alert: {result.get('error', 'unknown')}"
                )
                status_row.details = result
                status_row.last_checked_at = now
                if is_success:
                    status_row.last_success_at = now

            self.db.commit()
        except Exception as exc:
            logger.warning("Could not update integration_status for Feishu: %s", exc)
            self.db.rollback()
