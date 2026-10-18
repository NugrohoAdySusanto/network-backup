from __future__ import annotations

import logging
import re
import socket
import time
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    ReadTimeout,
)
from paramiko.ssh_exception import SSHException

from app.drivers.base import (
    BackupDriver,
    CollectedConfig,
    DeviceConnectionContext,
    DriverAuthenticationError,
    DriverCollectionError,
    DriverCommandTimeoutError,
    DriverConnectionError,
    DriverConnectionTimeoutError,
    DriverMetadata,
    DriverValidationError,
)

logger = logging.getLogger(__name__)


class ParametricCLIDriver(BackupDriver):
    """
    Generic, highly customizable SSH CLI driver for vendor switches, routers,
    and firewalls configured dynamically via Web GUI.
    """

    def __init__(self, definition: dict[str, Any]) -> None:
        self.key = definition.get("key", "custom-cli")
        self.label = definition.get("label", "Custom CLI Driver")
        self.vendor_hint = definition.get("vendor_hint", "Generic")
        self.model_hint = definition.get("model_hint", "Network Device")
        self.output_extension = definition.get("output_extension", "txt")
        self.default_port = int(definition.get("default_port", 22))
        self.connect_timeout = int(definition.get("connect_timeout", 15))
        self.command_timeout = int(definition.get("command_timeout", 60))
        
        self.need_enable = bool(definition.get("need_enable", False))
        self.enable_command = definition.get("enable_command", "enable")
        self.enable_prompt_pattern = definition.get("enable_prompt_pattern", r"[#$]")
        
        self.disable_paging_command = definition.get("disable_paging_command")
        self.paging_mode = definition.get("paging_mode", "none")  # none, command, interactive_space
        self.backup_command = definition.get("backup_command", "show running-config")
        
        self.strip_patterns = definition.get("strip_patterns") or []
        self.validation_min_length = int(definition.get("validation_min_length", 30))
        self.validation_required_keyword = definition.get("validation_required_keyword")

        self.metadata = DriverMetadata(
            key=self.key,
            label=self.label,
            transport="ssh",
            implementation="parametric_cli",
            output_extension=self.output_extension,
            vendor_hint=self.vendor_hint,
            model_hint=self.model_hint,
        )

        self._connection: Any | None = None
        self._context: DeviceConnectionContext | None = None

    def connect(self, context: DeviceConnectionContext) -> None:
        self._context = context
        port = context.port or self.default_port

        params = {
            "device_type": "generic_termserver",
            "host": context.host,
            "port": port,
            "username": context.username,
            "password": context.password,
            "conn_timeout": context.connect_timeout,
            "banner_timeout": max(context.connect_timeout, 15),
            "fast_cli": False,
        }

        try:
            self._connection = ConnectHandler(**params)
        except NetmikoAuthenticationException as exc:
            raise DriverAuthenticationError(
                f"SSH authentication failed for {context.hostname} ({context.host}:{port})"
            ) from exc
        except NetmikoTimeoutException as exc:
            raise DriverConnectionTimeoutError(
                f"SSH connection timed out connecting to {context.hostname} ({context.host}:{port})"
            ) from exc
        except (SSHException, socket.error, EOFError, OSError) as exc:
            raise DriverConnectionError(
                f"SSH transport error connecting to {context.hostname} ({context.host}:{port}): {exc}"
            ) from exc
        except Exception as exc:
            raise DriverConnectionError(
                f"Unexpected error establishing SSH connection to {context.hostname}: {exc}"
            ) from exc

        # Handle Privilege / Enable mode if needed
        if self.need_enable:
            enable_secret = context.enable_password or context.password
            try:
                self._connection.enable(
                    cmd=self.enable_command,
                    pattern=self.enable_prompt_pattern,
                    enable_pattern=self.enable_prompt_pattern,
                )
            except Exception as exc:
                # Fallback to direct command if Netmiko enable helper throws
                try:
                    out = self._connection.send_command_timing(self.enable_command)
                    if "password" in out.lower() and enable_secret:
                        self._connection.send_command_timing(enable_secret)
                except Exception as sub_exc:
                    raise DriverAuthenticationError(
                        f"Failed entering privilege/enable mode on {context.hostname}: {sub_exc}"
                    ) from sub_exc

        # Handle Paging Disable Command
        if self.disable_paging_command and self.disable_paging_command.strip():
            try:
                self._connection.send_command(self.disable_paging_command.strip())
            except Exception as exc:
                logger.warning("Could not execute disable_paging_command: %s", exc)

    def collect_config(self) -> CollectedConfig:
        if self._connection is None:
            raise DriverConnectionError("SSH connection is not established.")

        timeout = (self._context.command_timeout if self._context else 60)

        try:
            if self.paging_mode == "interactive_space":
                # Interactive paging mode (sends space on --More-- prompt)
                raw_output = self._collect_interactive_paging(timeout=timeout)
            else:
                raw_output = self._connection.send_command(
                    self.backup_command,
                    read_timeout=timeout,
                )

            return CollectedConfig(
                text=raw_output,
                extension=self.output_extension,
                encoding="utf-8",
            )
        except ReadTimeout as exc:
            raise DriverCommandTimeoutError(
                f"Timeout waiting for command '{self.backup_command}' on {self._context.hostname if self._context else 'device'}"
            ) from exc
        except Exception as exc:
            raise DriverCollectionError(
                f"Error collecting configuration via '{self.backup_command}': {exc}"
            ) from exc

    def _collect_interactive_paging(self, timeout: int) -> str:
        """Sends command and pages with spaces until completion."""
        chan = self._connection.find_prompt()
        self._connection.write_channel(self.backup_command + "\n")
        time.sleep(1)

        output_chunks: list[str] = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self._connection.channel.recv_ready():
                chunk = self._connection.channel.recv(4096).decode("utf-8", errors="ignore")
                output_chunks.append(chunk)

                if "--More--" in chunk or "---- More ----" in chunk:
                    self._connection.channel.send(" ")
                    time.sleep(0.2)
                    continue

            time.sleep(0.3)
            # Check if channel is idle
            if not self._connection.channel.recv_ready():
                break

        full_output = "".join(output_chunks)
        # Clean paging artifacts
        full_output = re.sub(r"--More--(\x1b\[[0-9;]*[a-zA-Z]|\s)*", "", full_output)
        full_output = re.sub(r"----\s*More\s*----", "", full_output)
        return full_output

    def normalize_config(self, collected: CollectedConfig) -> str:
        text = collected.text
        # 1. Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Strip user-defined volatile patterns
        if self.strip_patterns:
            for pat in self.strip_patterns:
                if pat and pat.strip():
                    try:
                        text = re.sub(pat.strip(), "", text, flags=re.MULTILINE)
                    except Exception as exc:
                        logger.warning("Invalid strip regex %s: %s", pat, exc)

        # 3. Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]
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
            raise DriverValidationError("Configuration collected from device is empty.")

        if len(trimmed) < self.validation_min_length:
            raise DriverValidationError(
                f"Configuration is too short ({len(trimmed)} bytes; minimum required is {self.validation_min_length})."
            )

        # Keyword validation
        if self.validation_required_keyword and self.validation_required_keyword.strip():
            req_word = self.validation_required_keyword.strip().lower()
            if req_word not in trimmed.lower():
                raise DriverValidationError(
                    f"Configuration missing required keyword validation: '{self.validation_required_keyword}'."
                )

    def cleanup(self) -> None:
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception:
                pass
            finally:
                self._connection = None
