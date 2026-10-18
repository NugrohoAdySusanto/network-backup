from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.drivers.base import (
    BackupDriver,
    DriverMetadata,
    DriverNotFoundError,
)
from app.drivers.mikrotik_routeros import MikrotikRouterOSDriver
from app.drivers.mock import MockBackupDriver
from app.drivers.parametric import ParametricCLIDriver
from app.drivers.ruijie_ap import RuijieAPDriver
from app.drivers.ruijie_switch import RuijieSwitchDriver
from app.drivers.sangfor_nsf import SangforNSFDriver

logger = logging.getLogger(__name__)


class DriverRegistry:
    def __init__(self) -> None:
        self._drivers: dict[str, type[BackupDriver]] = {}

    def register(self, driver_cls: type[BackupDriver]) -> None:
        key = driver_cls.metadata.key
        if key in self._drivers:
            raise RuntimeError(f"Duplicate driver key: {key}")
        self._drivers[key] = driver_cls

    def get(self, key: str) -> type[BackupDriver]:
        driver_cls = self._drivers.get(key)
        if driver_cls is not None:
            return driver_cls
        raise DriverNotFoundError(f"Unknown static driver class: {key}")

    def create(self, key: str) -> BackupDriver:
        # 1. Check built-in static drivers
        if key in self._drivers:
            return self._drivers[key]()

        # 2. Check dynamic custom drivers from Database
        custom_driver = self._lookup_custom_driver(key)
        if custom_driver is not None:
            return ParametricCLIDriver(custom_driver)

        raise DriverNotFoundError(f"Backup driver '{key}' is not registered.")

    def has(self, key: str) -> bool:
        if key in self._drivers:
            return True
        return self._lookup_custom_driver(key) is not None

    def list_metadata(self) -> list[DriverMetadata]:
        # Built-in static drivers
        results = [
            driver_cls.metadata
            for _, driver_cls in sorted(self._drivers.items())
        ]

        # Merge active custom drivers from Database
        custom_list = self._list_all_custom_drivers()
        for cd in custom_list:
            results.append(
                DriverMetadata(
                    key=cd["key"],
                    label=cd["label"],
                    transport=cd.get("transport", "ssh"),
                    implementation="parametric_cli",
                    output_extension=cd.get("output_extension", "txt"),
                    vendor_hint=cd.get("vendor_hint", "Generic"),
                    model_hint=cd.get("model_hint", "Network Device"),
                )
            )

        return results

    def _lookup_custom_driver(self, key: str) -> dict[str, Any] | None:
        try:
            from app.database import new_session
            from app.models.custom_driver import CustomDriver
            with new_session() as db:
                row = db.query(CustomDriver).filter_by(key=key, is_active=True).first()
                if row:
                    return {
                        "key": row.key,
                        "label": row.label,
                        "vendor_hint": row.vendor_hint,
                        "model_hint": row.model_hint,
                        "transport": row.transport,
                        "default_port": row.default_port,
                        "connect_timeout": row.connect_timeout,
                        "command_timeout": row.command_timeout,
                        "need_enable": row.need_enable,
                        "enable_command": row.enable_command,
                        "enable_prompt_pattern": row.enable_prompt_pattern,
                        "disable_paging_command": row.disable_paging_command,
                        "paging_mode": row.paging_mode,
                        "backup_command": row.backup_command,
                        "output_extension": row.output_extension,
                        "strip_patterns": row.strip_patterns,
                        "validation_min_length": row.validation_min_length,
                        "validation_required_keyword": row.validation_required_keyword,
                    }
        except Exception as exc:
            logger.warning("Error querying custom driver for key '%s': %s", key, exc)
        return None

    def _list_all_custom_drivers(self) -> list[dict[str, Any]]:
        try:
            from app.database import new_session
            from app.models.custom_driver import CustomDriver
            with new_session() as db:
                rows = db.query(CustomDriver).filter_by(is_active=True).all()
                return [
                    {
                        "key": r.key,
                        "label": r.label,
                        "vendor_hint": r.vendor_hint,
                        "model_hint": r.model_hint,
                        "transport": r.transport,
                        "output_extension": r.output_extension,
                    }
                    for r in rows
                ]
        except Exception:
            return []


registry = DriverRegistry()
registry.register(SangforNSFDriver)
registry.register(MikrotikRouterOSDriver)
registry.register(RuijieSwitchDriver)
registry.register(RuijieAPDriver)

if settings.enable_mock_driver and settings.app_env != "production":
    registry.register(MockBackupDriver)
