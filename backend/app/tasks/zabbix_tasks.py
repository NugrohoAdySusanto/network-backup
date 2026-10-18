
from __future__ import annotations

from app.celery_app import celery_app
from app.database import new_session
from app.services.zabbix_service import ZabbixService


@celery_app.task(name="network_backup.sync_zabbix_devices")
def sync_zabbix_devices() -> dict[str, int | str]:
    with new_session() as db:
        result = ZabbixService(db).sync_network_devices()
        return {
            "status": "ok",
            "synced": result.synced,
            "marked_missing": result.marked_missing,
        }
