
from __future__ import annotations

from app.drivers.base import (
    BackupDriver,
    CollectedConfig,
    DeviceConnectionContext,
    DriverMetadata,
    DriverValidationError,
)


class MockBackupDriver(BackupDriver):
    metadata = DriverMetadata(
        key="mock-backup",
        label="Mock Backup Driver (Development Only)",
        transport="mock",
        implementation="mock",
        output_extension="cfg",
        vendor_hint="Development",
    )

    def __init__(self) -> None:
        self._connected = False
        self._context: DeviceConnectionContext | None = None

    def connect(self, context: DeviceConnectionContext) -> None:
        self._context = context
        self._connected = True

    def collect_config(self) -> CollectedConfig:
        if not self._connected or self._context is None:
            raise RuntimeError("Mock driver is not connected.")
        return CollectedConfig(
            text=(
                f"hostname {self._context.hostname}\n"
                "interface mock0\n"
                " description C5-development-test\n"
            ),
            extension="cfg",
        )

    def normalize_config(self, collected: CollectedConfig) -> str:
        return collected.text.replace("\r\n", "\n").strip() + "\n"

    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None:
        if not normalized_text.strip():
            raise DriverValidationError("Mock config is empty.")

    def cleanup(self) -> None:
        self._connected = False
        self._context = None
