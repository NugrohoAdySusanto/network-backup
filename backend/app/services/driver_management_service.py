from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.drivers.base import DeviceConnectionContext
from app.drivers.parametric import ParametricCLIDriver
from app.drivers.registry import registry
from app.models.backup_setting import DeviceBackupSetting
from app.models.custom_driver import CustomDriver
from app.models.device import Device

logger = logging.getLogger(__name__)


class DriverManagementService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_drivers(self) -> list[dict[str, Any]]:
        """
        Lists all available backup drivers, identifying whether each is built-in or custom.
        """
        builtin_keys = set(registry._drivers.keys())
        custom_rows = self.db.scalars(
            select(CustomDriver).order_by(CustomDriver.created_at.asc())
        ).all()
        custom_map = {r.key: r for r in custom_rows}

        results: list[dict[str, Any]] = []

        # 1. Built-in drivers
        for meta in sorted(registry._drivers.values(), key=lambda d: d.metadata.key):
            m = meta.metadata
            results.append({
                "key": m.key,
                "label": m.label,
                "vendor_hint": m.vendor_hint,
                "model_hint": m.model_hint,
                "transport": m.transport,
                "output_extension": m.output_extension,
                "is_builtin": True,
                "is_active": True,
            })

        # 2. Custom drivers
        for r in custom_rows:
            results.append({
                "id": str(r.id),
                "key": r.key,
                "label": r.label,
                "vendor_hint": r.vendor_hint,
                "model_hint": r.model_hint,
                "transport": r.transport,
                "default_port": r.default_port,
                "connect_timeout": r.connect_timeout,
                "command_timeout": r.command_timeout,
                "need_enable": r.need_enable,
                "enable_command": r.enable_command,
                "disable_paging_command": r.disable_paging_command,
                "paging_mode": r.paging_mode,
                "backup_command": r.backup_command,
                "output_extension": r.output_extension,
                "strip_patterns": r.strip_patterns,
                "validation_min_length": r.validation_min_length,
                "validation_required_keyword": r.validation_required_keyword,
                "is_builtin": False,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat(),
            })

        return results

    def create_custom_driver(self, data: dict[str, Any]) -> CustomDriver:
        key = data.get("key", "").strip().lower()
        if not key:
            raise AppError(422, "INVALID_DRIVER_KEY", "Driver key is required.")

        if key in registry._drivers:
            raise AppError(409, "KEY_CONFLICT", f"Key '{key}' conflicts with a built-in driver.")

        existing = self.db.scalar(select(CustomDriver).where(CustomDriver.key == key))
        if existing:
            raise AppError(409, "KEY_CONFLICT", f"A driver with key '{key}' already exists.")

        driver = CustomDriver(
            id=uuid.uuid4(),
            key=key,
            label=data.get("label", key).strip(),
            vendor_hint=data.get("vendor_hint", "Generic").strip(),
            model_hint=data.get("model_hint", "Network Device").strip(),
            transport=data.get("transport", "ssh").strip(),
            default_port=int(data.get("default_port", 22)),
            connect_timeout=int(data.get("connect_timeout", 15)),
            command_timeout=int(data.get("command_timeout", 60)),
            need_enable=bool(data.get("need_enable", False)),
            enable_command=data.get("enable_command", "enable").strip(),
            enable_prompt_pattern=data.get("enable_prompt_pattern", r"[#$]"),
            disable_paging_command=data.get("disable_paging_command") or None,
            paging_mode=data.get("paging_mode", "none"),
            backup_command=data.get("backup_command", "show running-config").strip(),
            output_extension=data.get("output_extension", "txt").strip().lstrip("."),
            strip_patterns=data.get("strip_patterns") or [],
            validation_min_length=int(data.get("validation_min_length", 30)),
            validation_required_keyword=data.get("validation_required_keyword") or None,
            is_active=bool(data.get("is_active", True)),
        )
        self.db.add(driver)
        self.db.commit()
        self.db.refresh(driver)
        return driver

    def update_custom_driver(self, key: str, data: dict[str, Any]) -> CustomDriver:
        driver = self.db.scalar(select(CustomDriver).where(CustomDriver.key == key))
        if not driver:
            raise AppError(404, "DRIVER_NOT_FOUND", f"Custom driver '{key}' not found.")

        for field in [
            "label", "vendor_hint", "model_hint", "transport", "default_port",
            "connect_timeout", "command_timeout", "need_enable", "enable_command",
            "enable_prompt_pattern", "disable_paging_command", "paging_mode",
            "backup_command", "output_extension", "strip_patterns",
            "validation_min_length", "validation_required_keyword", "is_active",
        ]:
            if field in data:
                setattr(driver, field, data[field])

        self.db.commit()
        self.db.refresh(driver)
        return driver

    def delete_custom_driver(self, key: str) -> None:
        driver = self.db.scalar(select(CustomDriver).where(CustomDriver.key == key))
        if not driver:
            raise AppError(404, "DRIVER_NOT_FOUND", f"Custom driver '{key}' not found.")

        # Check if assigned to any device
        assigned_count = self.db.scalar(
            select(DeviceBackupSetting).where(DeviceBackupSetting.driver_key == key)
        )
        if assigned_count:
            raise AppError(
                409,
                "DRIVER_IN_USE",
                f"Driver '{key}' is currently assigned to devices. Reassign those devices first.",
            )

        self.db.delete(driver)
        self.db.commit()

    def test_driver(self, data: dict[str, Any], device_id: int) -> dict[str, Any]:
        """
        Tests the parametric driver against a live device to verify SSH collection.
        Returns preview snippet of the captured configuration.
        """
        device = self.db.scalar(select(Device).where(Device.id == device_id))
        if not device:
            raise AppError(404, "DEVICE_NOT_FOUND", "Test device not found.")

        driver_instance = ParametricCLIDriver(data)
        device_ip = str(device.ip_address).split("/")[0]

        context = DeviceConnectionContext(
            device_id=device.id,
            hostname=device.hostname,
            host=device_ip,
            port=driver_instance.default_port or settings.network_ssh_port,
            username=data.get("username") or settings.network_ssh_username,
            password=data.get("password") or settings.network_ssh_password,
            connect_timeout=getattr(driver_instance, "connect_timeout", 15),
            command_timeout=getattr(driver_instance, "command_timeout", 60),
            enable_password=data.get("enable_password") or settings.network_ssh_enable_password or None,
        )

        try:
            driver_instance.connect(context)
            collected = driver_instance.collect_config()
            normalized = driver_instance.normalize_config(collected)
            driver_instance.validate_config(collected, normalized)
            preview = normalized[:1000] + ("\n... [truncated]" if len(normalized) > 1000 else "")
            return {
                "success": True,
                "message": f"Test connection to {device.hostname} succeeded!",
                "raw_size_bytes": len(collected.text),
                "normalized_size_bytes": len(normalized),
                "preview": preview,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Test connection failed: {exc}",
                "error_details": str(exc),
            }
        finally:
            driver_instance.cleanup()
