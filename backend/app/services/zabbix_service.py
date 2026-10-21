
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.integrations.zabbix_client import (
    ZabbixClient,
    ZabbixClientError,
)
from app.repositories.device_repository import DeviceRepository
from app.repositories.integration_status_repository import (
    IntegrationStatusRepository,
)


@dataclass(frozen=True)
class SyncResult:
    synced: int
    marked_missing: int


class ZabbixService:
    def __init__(
        self,
        db: Session,
        *,
        client: ZabbixClient | None = None,
    ) -> None:
        self.db = db
        self.client = client or ZabbixClient()
        self.devices = DeviceRepository(db)
        self.integration_status = IntegrationStatusRepository(db)

    def sync_network_devices(self) -> SyncResult:
        checked_at = datetime.now(timezone.utc)

        try:
            records = self.client.build_host_records(
                group_id=settings.zabbix_network_group_id,
                item_key=settings.zabbix_availability_item_key,
            )
        except ZabbixClientError as exc:
            self.integration_status.upsert(
                name="zabbix_sync",
                status="ERROR",
                summary="Unable to synchronize devices from Zabbix.",
                details={"reason": str(exc)},
                checked_at=checked_at,
                success=False,
            )
            self.db.commit()
            raise

        seen: set[str] = set()
        for record in records:
            seen.add(record.host_id)
            self.devices.upsert_from_zabbix(
                zabbix_host_id=record.host_id,
                hostname=record.hostname,
                ip_address=record.ip_address,
                vendor=record.vendor,
                model=record.model,
                host_group="Network Device",
                availability_status=record.availability_status,
                availability_checked_at=record.availability_checked_at,
                sync_time=checked_at,
            )

        missing = self.devices.mark_missing_sources(
            seen_host_ids=seen,
            sync_time=checked_at,
        )

        self.integration_status.upsert(
            name="zabbix_sync",
            status="OK",
            summary=f"{len(records)} network devices synchronized.",
            details={
                "device_count": len(records),
                "marked_missing": missing,
            },
            checked_at=checked_at,
            success=True,
        )
        self.db.commit()

        from app.services.audit_log_service import AuditLogService
        AuditLogService.record_event_standalone(
            category="AUDIT",
            severity="INFO",
            event_type="INVENTORY_SYNC_COMPLETED",
            message=f"Network device inventory sync completed: {len(records)} devices synchronized, {missing} marked missing.",
            endpoint="Celery Task: sync_zabbix_devices",
            details={
                "device_count": len(records),
                "marked_missing": missing,
            },
        )

        return SyncResult(
            synced=len(records),
            marked_missing=missing,
        )

    def get_live_availability(
        self,
        zabbix_host_id: str,
    ) -> tuple[str, datetime | None]:
        return self.client.get_live_availability(
            zabbix_host_id,
            settings.zabbix_availability_item_key,
        )
