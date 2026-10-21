from __future__ import annotations

import logging
import socket
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    ReadTimeout,
)
from paramiko.client import MissingHostKeyPolicy
from paramiko.ssh_exception import SSHException

from app.drivers.base import (
    BackupDriver,
    DeviceConnectionContext,
    DriverAuthenticationError,
    DriverCollectionError,
    DriverCommandTimeoutError,
    DriverConnectionError,
    DriverConnectionTimeoutError,
)

logger = logging.getLogger(__name__)


class ResilientAutoAddPolicy(MissingHostKeyPolicy):
    """
    Paramiko MissingHostKeyPolicy that adds the host key in-memory and attempts
    to persist it to known_hosts. If disk persistence fails due to permissions
    or OS restrictions, it silently proceeds in-memory so SSH is never aborted.
    """
    def missing_host_key(self, client: Any, hostname: str, key: Any) -> None:
        client._host_keys.add(hostname, key.get_name(), key)
        if getattr(client, "_host_keys_filename", None) is not None:
            try:
                client.save_host_keys(client._host_keys_filename)
            except (OSError, PermissionError) as exc:
                logger.debug(
                    "Suppressed known_hosts persistence failure for %s (%s): %s",
                    hostname,
                    client._host_keys_filename,
                    exc,
                )


class BaseNetmikoDriver(BackupDriver):
    """
    Common base class for drivers utilizing Netmiko SSH transport.
    Maps underlying Netmiko/Paramiko exceptions into contractual DriverErrors.
    """

    netmiko_device_type: str = "generic_termserver"

    def __init__(self) -> None:
        self._connection: Any | None = None
        self._context: DeviceConnectionContext | None = None

    def get_connection_parameters(
        self,
        context: DeviceConnectionContext,
    ) -> dict[str, Any]:
        import os
        from app.config import settings

        params: dict[str, Any] = {
            "device_type": self.netmiko_device_type,
            "host": context.host,
            "port": context.port,
            "username": context.username,
            "password": context.password,
            "conn_timeout": context.connect_timeout,
            "banner_timeout": max(context.connect_timeout, 15),
            "fast_cli": False,
            "ssh_strict": settings.ssh_strict_host_key_checking,
            "system_host_keys": True,
        }
        if settings.ssh_known_hosts_path and os.path.isfile(settings.ssh_known_hosts_path):
            params["alt_host_keys"] = True
            params["alt_key_file"] = settings.ssh_known_hosts_path
        return params

    def connect(self, context: DeviceConnectionContext) -> None:
        self._context = context
        params = self.get_connection_parameters(context)

        import paramiko
        from paramiko.client import MissingHostKeyPolicy
        from paramiko.rsakey import RSAKey
        from cryptography.hazmat.primitives import hashes
        from app.config import settings

        # Enable legacy ssh-rsa host key algorithm for enterprise network equipment
        if "ssh-rsa" not in RSAKey.HASHES:
            RSAKey.HASHES["ssh-rsa"] = hashes.SHA1
        if "ssh-rsa" not in paramiko.Transport._key_info:
            paramiko.Transport._key_info["ssh-rsa"] = RSAKey
        if "ssh-rsa" not in paramiko.Transport._preferred_keys:
            paramiko.Transport._preferred_keys = list(paramiko.Transport._preferred_keys) + ["ssh-rsa"]

        # Ensure non-strict mode does not crash when known_hosts is unwritable
        if not settings.ssh_strict_host_key_checking:
            paramiko.AutoAddPolicy = ResilientAutoAddPolicy  # type: ignore[misc]
            paramiko.client.AutoAddPolicy = ResilientAutoAddPolicy  # type: ignore[misc]

        try:
            self._connection = ConnectHandler(**params)
        except NetmikoAuthenticationException as exc:
            raise DriverAuthenticationError(
                f"SSH authentication failed for {context.hostname} ({context.host}:{context.port})"
            ) from exc
        except NetmikoTimeoutException as exc:
            raise DriverConnectionTimeoutError(
                f"SSH connection timed out connecting to {context.hostname} ({context.host}:{context.port})"
            ) from exc
        except (SSHException, socket.error, EOFError, OSError) as exc:
            raise DriverConnectionError(
                f"SSH transport error connecting to {context.hostname} ({context.host}:{context.port}): {exc}"
            ) from exc
        except Exception as exc:
            raise DriverConnectionError(
                f"Unexpected error establishing SSH connection to {context.hostname}: {exc}"
            ) from exc

    def send_command(
        self,
        command: str,
        *,
        read_timeout: int | None = None,
    ) -> str:
        if self._connection is None:
            raise DriverConnectionError("SSH connection is not established.")

        timeout = read_timeout
        if timeout is None and self._context is not None:
            timeout = self._context.command_timeout

        try:
            return self._connection.send_command(
                command,
                read_timeout=timeout or 60,
            )
        except ReadTimeout as exc:
            raise DriverCommandTimeoutError(
                f"Timeout waiting for response to command '{command}'"
            ) from exc
        except Exception as exc:
            raise DriverCollectionError(
                f"Failed to execute command '{command}': {exc}"
            ) from exc

    def cleanup(self) -> None:
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception as exc:
                logger.warning("Error during driver cleanup disconnect: %s", exc)
            finally:
                self._connection = None
