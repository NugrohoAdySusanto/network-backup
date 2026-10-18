
from datetime import datetime, timezone

from app.integrations.zabbix_client import ZabbixClient


def test_icmp_up_value_maps_to_up() -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    status, checked_at = ZabbixClient._normalize_item_availability(
        {
            "lastclock": str(now),
            "lastvalue": "1",
            "status": "0",
            "state": "0",
        }
    )
    assert status == "up"
    assert checked_at is not None


def test_icmp_zero_maps_to_down() -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    status, _ = ZabbixClient._normalize_item_availability(
        {
            "lastclock": str(now),
            "lastvalue": "0",
            "status": "0",
            "state": "0",
        }
    )
    assert status == "down"


def test_unsupported_item_maps_to_unknown() -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    status, _ = ZabbixClient._normalize_item_availability(
        {
            "lastclock": str(now),
            "lastvalue": "1",
            "status": "0",
            "state": "1",
        }
    )
    assert status == "unknown"
