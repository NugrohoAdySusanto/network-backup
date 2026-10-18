
from __future__ import annotations

from app.drivers.base import (
    BackupDriver,
    CollectedConfig,
    DeviceConnectionContext,
    DriverNotImplementedError,
)


class MetadataOnlyDriver(BackupDriver):
    """
    C4 metadata/assignment placeholder.

    Real vendor commands are deliberately not implemented here.
    C6 replaces each production driver's methods after verified device PoC.
    """

    def connect(self, context: DeviceConnectionContext) -> None:
        raise DriverNotImplementedError(
            f"{self.metadata.key} is registered but its real SSH "
            "collection routine is not implemented yet."
        )

    def collect_config(self) -> CollectedConfig:
        raise DriverNotImplementedError

    def normalize_config(self, collected: CollectedConfig) -> str:
        raise DriverNotImplementedError

    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None:
        raise DriverNotImplementedError

    def cleanup(self) -> None:
        return None
