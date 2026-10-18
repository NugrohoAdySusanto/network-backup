from __future__ import annotations

import logging
import re
import socket
import time

import paramiko
from paramiko.ssh_exception import (
    AuthenticationException,
    SSHException,
)

from app.drivers.base import (
    BackupDriver,
    CollectedConfig,
    DeviceConnectionContext,
    DriverAuthenticationError,
    DriverCommandTimeoutError,
    DriverConnectionError,
    DriverConnectionTimeoutError,
    DriverMetadata,
    DriverValidationError,
)

logger = logging.getLogger(__name__)


class SangforNSFDriver(BackupDriver):
    metadata = DriverMetadata(
        key="sangfor-nsf",
        label="Sangfor NSF Driver",
        transport="ssh",
        implementation="paramiko",
        output_extension="txt",
        vendor_hint="Sangfor",
        model_hint="NSF",
    )

    export_command = "show running-configuration"

    def __init__(self) -> None:
        self._client: paramiko.SSHClient | None = None
        self._channel: paramiko.Channel | None = None
        self._context: DeviceConnectionContext | None = None

    def connect(self, context: DeviceConnectionContext) -> None:
        import os
        from app.config import settings

        self._context = context
        self._client = paramiko.SSHClient()
        self._client.load_system_host_keys()
        if settings.ssh_known_hosts_path and os.path.isfile(settings.ssh_known_hosts_path):
            try:
                self._client.load_host_keys(settings.ssh_known_hosts_path)
            except Exception as exc:
                logger.warning("Could not load known hosts file %s: %s", settings.ssh_known_hosts_path, exc)

        if settings.ssh_strict_host_key_checking:
            self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


        try:
            self._client.connect(
                hostname=context.host,
                port=context.port,
                username=context.username,
                password=context.password,
                timeout=context.connect_timeout or 15,
                look_for_keys=False,
                allow_agent=False,
            )
            self._channel = self._client.invoke_shell(width=200, height=100)
            time.sleep(1)

            # Flush initial welcome banner
            while self._channel.recv_ready():
                self._channel.recv(65535)

        except AuthenticationException as exc:
            self.disconnect()
            raise DriverAuthenticationError(
                f"SSH authentication failed for {context.hostname} ({context.host}:{context.port})"
            ) from exc
        except (socket.timeout, TimeoutError) as exc:
            self.disconnect()
            raise DriverConnectionTimeoutError(
                f"SSH connection timed out connecting to {context.hostname} ({context.host}:{context.port})"
            ) from exc
        except (SSHException, socket.error, EOFError, OSError) as exc:
            self.disconnect()
            raise DriverConnectionError(
                f"SSH transport error connecting to {context.hostname} ({context.host}:{context.port}): {exc}"
            ) from exc
        except Exception as exc:
            self.disconnect()
            raise DriverConnectionError(
                f"Unexpected error establishing SSH connection to {context.hostname}: {exc}"
            ) from exc

    def collect_config(self) -> CollectedConfig:
        if self._channel is None or self._client is None:
            raise DriverConnectionError("SSH connection is not established.")

        cmd = f"{self.export_command}\n"
        self._channel.send(cmd)

        full_output = ""
        command_timeout = (self._context.command_timeout if self._context else 60) or 60
        start_time = time.time()
        last_recv_time = time.time()

        while time.time() - start_time < command_timeout:
            if self._channel.recv_ready():
                chunk = self._channel.recv(65535).decode("utf-8", errors="ignore")
                full_output += chunk
                last_recv_time = time.time()

                # Handle --More-- pagination
                if "--More--" in chunk or full_output.rstrip().endswith("--More--"):
                    self._channel.send(" ")
                # Check for return to prompt (e.g. backupadmin# )
                elif re.search(r"backupadmin#\s*$", full_output) and len(full_output) > 200:
                    break
            else:
                if time.time() - last_recv_time > 3 and len(full_output) > 200:
                    break
                time.sleep(0.1)

        if time.time() - start_time >= command_timeout and not full_output:
            raise DriverCommandTimeoutError(
                f"Timeout waiting for response to command '{self.export_command}'"
            )

        # Remove command echo, ANSI control sequences, and --More-- artifacts
        cleaned = re.sub(r"^(?:backupadmin#\s*)?show running-configuration\s*\r?\n?", "", full_output, flags=re.MULTILINE)
        cleaned = re.sub(r"--More--(?:\x1b\[[0-9;]*[a-zA-Z]|\s)*", "", cleaned)
        cleaned = re.sub(r"backupadmin#\s*$", "", cleaned).strip()

        return CollectedConfig(
            text=cleaned,
            extension=self.metadata.output_extension,
            filename="config.txt",
            encoding="utf-8",
        )

    def disconnect(self) -> None:
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def cleanup(self) -> None:
        self.disconnect()

    def normalize_config(self, collected: CollectedConfig) -> str:
        text = collected.text

        # 1. Normalize line endings to LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Strip leading prompt/echo if present
        text = re.sub(r"^(?:backupadmin#\s*)?show running-configuration\s*\n?", "", text, flags=re.MULTILINE)

        # 3. Strip trailing prompt
        text = re.sub(r"^backupadmin#\s*$", "", text, flags=re.MULTILINE)

        # 4. Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]

        # 5. Remove leading and trailing empty lines
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        if not lines:
            return ""

        return "\n".join(lines) + "\n"

    def validate_config(
        self,
        collected: CollectedConfig,
        normalized_text: str,
    ) -> None:
        trimmed = normalized_text.strip()
        if not trimmed:
            raise DriverValidationError("Collected Sangfor NSF configuration is empty.")

        if len(trimmed) < 100:
            raise DriverValidationError(
                f"Sangfor NSF configuration is too short ({len(trimmed)} bytes)."
            )

        lower = trimmed.lower()
        cli_errors = [
            "parameters are incorrect",
            "command not found",
            "syntax error",
            "permission denied",
        ]
        for error in cli_errors:
            if error in lower:
                raise DriverValidationError(
                    f"Sangfor output contains CLI error message: '{error}'"
                )

        if "config" not in lower:
            raise DriverValidationError(
                "Sangfor configuration validation failed: expected 'config' blocks not found."
            )
