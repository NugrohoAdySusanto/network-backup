
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings


class ZabbixClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZabbixHostRecord:
    host_id: str
    hostname: str
    ip_address: str
    vendor: str | None
    model: str | None
    availability_status: str
    availability_checked_at: datetime | None


class ZabbixClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.zabbix_url).rstrip("/")
        self.api_token = api_token or settings.zabbix_api_token
        self.timeout = timeout
        self._ids = itertools.count(1)

    @property
    def api_url(self) -> str:
        if self.base_url.endswith("/api_jsonrpc.php"):
            return self.base_url
        return f"{self.base_url}/api_jsonrpc.php"

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        if not self.base_url:
            raise ZabbixClientError("Zabbix URL is not configured.")
        if not self.api_token:
            raise ZabbixClientError("Zabbix API token is not configured.")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": next(self._ids),
        }

        headers = {
            "Content-Type": "application/json-rpc",
            "Authorization": f"Bearer {self.api_token}",
        }

        try:
            with httpx.Client(timeout=self.timeout, verify=True) as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ZabbixClientError(
                "Unable to communicate with Zabbix API."
            ) from exc

        if "error" in body:
            error = body["error"]
            raise ZabbixClientError(
                f"Zabbix API error {error.get('code')}: "
                f"{error.get('message', 'Unknown error')}"
            )

        return body.get("result")

    def get_network_hosts(self, group_id: str) -> list[dict[str, Any]]:
        result = self._rpc(
            "host.get",
            {
                "groupids": [group_id],
                "output": ["hostid", "host", "name", "status"],
                "selectInterfaces": [
                    "interfaceid",
                    "ip",
                    "dns",
                    "useip",
                    "main",
                    "type",
                ],
                "selectInventory": ["vendor", "model"],
            },
        )
        return list(result or [])

    def get_availability_items(
        self,
        host_ids: list[str],
        item_key: str,
    ) -> list[dict[str, Any]]:
        if not host_ids:
            return []

        result = self._rpc(
            "item.get",
            {
                "hostids": host_ids,
                "output": [
                    "itemid",
                    "hostid",
                    "key_",
                    "lastvalue",
                    "lastclock",
                    "status",
                    "state",
                ],
                "search": {"key_": item_key},
            },
        )

        # Zabbix search may match similarly named keys. Keep exact key only.
        return [
            item
            for item in (result or [])
            if str(item.get("key_", "")) == item_key
        ]

    def get_live_availability(
        self,
        host_id: str,
        item_key: str,
    ) -> tuple[str, datetime | None]:
        items = self.get_availability_items([host_id], item_key)
        if not items:
            return "unknown", None

        # One exact item is expected. If there are multiple, newest wins.
        item = max(
            items,
            key=lambda value: int(value.get("lastclock") or 0),
        )
        return self._normalize_item_availability(item)

    def build_host_records(
        self,
        *,
        group_id: str,
        item_key: str,
    ) -> list[ZabbixHostRecord]:
        hosts = self.get_network_hosts(group_id)
        host_ids = [str(host["hostid"]) for host in hosts]
        items = self.get_availability_items(host_ids, item_key)

        items_by_host: dict[str, dict[str, Any]] = {}
        for item in items:
            host_id = str(item.get("hostid"))
            existing = items_by_host.get(host_id)
            if existing is None or int(item.get("lastclock") or 0) > int(
                existing.get("lastclock") or 0
            ):
                items_by_host[host_id] = item

        records: list[ZabbixHostRecord] = []
        for host in hosts:
            host_id = str(host["hostid"])
            interface = self._select_management_interface(
                list(host.get("interfaces") or [])
            )
            inventory = host.get("inventory") or {}
            item = items_by_host.get(host_id)

            if item is None:
                availability, checked_at = "unknown", None
            else:
                availability, checked_at = self._normalize_item_availability(
                    item
                )

            records.append(
                ZabbixHostRecord(
                    host_id=host_id,
                    hostname=str(
                        host.get("name")
                        or host.get("host")
                        or host_id
                    ),
                    ip_address=self._interface_address(interface),
                    vendor=self._clean_optional(inventory.get("vendor")),
                    model=self._clean_optional(inventory.get("model")),
                    availability_status=availability,
                    availability_checked_at=checked_at,
                )
            )

        return records

    @staticmethod
    def _select_management_interface(
        interfaces: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not interfaces:
            raise ZabbixClientError(
                "Zabbix host has no management interface."
            )

        main_interfaces = [
            interface
            for interface in interfaces
            if str(interface.get("main", "0")) == "1"
        ]
        candidates = main_interfaces or interfaces
        return candidates[0]

    @staticmethod
    def _interface_address(interface: dict[str, Any]) -> str:
        use_ip = str(interface.get("useip", "1")) == "1"
        address = (
            interface.get("ip")
            if use_ip
            else interface.get("dns")
        )
        value = str(address or "").strip()
        if not value:
            raise ZabbixClientError(
                "Zabbix management interface has no address."
            )
        return value

    @staticmethod
    def _clean_optional(value: Any) -> str | None:
        cleaned = str(value or "").strip()
        return cleaned or None

    @staticmethod
    def _normalize_item_availability(
        item: dict[str, Any],
    ) -> tuple[str, datetime | None]:
        try:
            lastclock = int(item.get("lastclock") or 0)
        except (TypeError, ValueError):
            lastclock = 0

        checked_at = (
            datetime.fromtimestamp(lastclock, tz=timezone.utc)
            if lastclock > 0
            else None
        )

        # Disabled item or unsupported item state is not a valid UP/DOWN source.
        if str(item.get("status", "0")) != "0":
            return "unknown", checked_at
        if str(item.get("state", "0")) != "0":
            return "unknown", checked_at

        if checked_at is None:
            return "unknown", None

        age = (
            datetime.now(timezone.utc) - checked_at
        ).total_seconds()
        if age > settings.zabbix_availability_max_age_seconds:
            return "unknown", checked_at

        value = str(item.get("lastvalue", "")).strip()
        if value == "1":
            return "up", checked_at
        if value == "0":
            return "down", checked_at
        return "unknown", checked_at
