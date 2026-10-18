from __future__ import annotations

from dataclasses import asdict
from app.celery_app import celery_app
from app.integrations.ceph_health_client import CephHealthClient


@celery_app.task(name="network_backup.refresh_ceph_health")
def refresh_ceph_health() -> dict[str, str]:
    client = CephHealthClient()
    result = client.get_health()
    return asdict(result)
