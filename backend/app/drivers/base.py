
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DriverMetadata:
    key: str
    label: str
    transport: str
    implementation: str
    output_extension: str
    vendor_hint: str | None = None
    model_hint: str | None = None


@dataclass(frozen=True, repr=False)
class DeviceConnectionContext:
    device_id: int
    hostname: str
    host: str
    port: int
    username: str
    password: str
    connect_timeout: int
    command_timeout: int
    enable_password: str | None = None

    def __repr__(self) -> str:
        return (
            f"DeviceConnectionContext(device_id={self.device_id}, "
            f"hostname='{self.hostname}', host='{self.host}', port={self.port}, "
            f"username='{self.username}', password='***', enable_password='***')"
        )

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(frozen=True)
class CollectedConfig:
    text: str
    extension: str
    encoding: str = "utf-8"
    filename: str | None = None


class DriverError(Exception):
    code = "DRIVER_ERROR"
    retryable = False


class DriverConfigurationError(DriverError):
    code = "DRIVER_CONFIGURATION_ERROR"
    retryable = False


class DriverNotFoundError(DriverError):
    code = "DRIVER_NOT_FOUND"


class DriverNotImplementedError(DriverError):
    code = "DRIVER_NOT_IMPLEMENTED"


class DriverConnectionError(DriverError):
    code = "SSH_TRANSPORT_ERROR"
    retryable = True


class DriverAuthenticationError(DriverError):
    code = "AUTHENTICATION_FAILED"


class DriverConnectionTimeoutError(DriverError):
    code = "CONNECTION_TIMEOUT"
    retryable = True


class DriverCommandTimeoutError(DriverError):
    code = "COMMAND_TIMEOUT"
    retryable = True


class DriverCollectionError(DriverError):
    code = "COMMAND_FAILED"


class DriverNormalizationError(DriverError):
    code = "NORMALIZATION_FAILED"


class DriverValidationError(DriverError):
    code = "INVALID_CONFIG"


class BackupDriver(ABC):
    metadata: DriverMetadata

    @abstractmethod
    def connect(self, context: DeviceConnectionContext) -> None:
        raise NotImplementedError

    @abstractmethod
    def collect_config(self) -> CollectedConfig:
        raise NotImplementedError

    @abstractmethod
    def normalize_config(self, collected: CollectedConfig) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup(self) -> None:
        raise NotImplementedError
