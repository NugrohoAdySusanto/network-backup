from __future__ import annotations

from dataclasses import replace
import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


from app.drivers.base import (
    CollectedConfig,
    DeviceConnectionContext,
    DriverConfigurationError,
    DriverMetadata,
    DriverValidationError,
)
from app.drivers.netmiko_base import BaseNetmikoDriver


class RuijieSwitchDriver(BaseNetmikoDriver):
    metadata = DriverMetadata(
        key="ruijie-switch",
        label="Ruijie Switch Driver",
        transport="ssh",
        implementation="netmiko",
        output_extension="txt",
        vendor_hint="Ruijie Networks",
        model_hint="Switch",
    )

    netmiko_device_type = "ruijie_os"
    export_command = "show running-config"
    default_port: int = 22

    def connect(self, context: DeviceConnectionContext) -> None:
        # Enforce standard SSH port 22 specifically for Ruijie Switch (overriding default/environment port e.g. 22345)
        if context.port != self.default_port:
            context = replace(context, port=self.default_port)

        import hashlib
        import paramiko
        from cryptography.hazmat.primitives import hashes
        from paramiko.kex_gex import KexGexSHA256
        from paramiko.kex_group14 import KexGroup14SHA256
        from paramiko.rsakey import RSAKey

        # Snapshot original paramiko global transport preferences before temporarily applying device exceptions
        orig_preferred_keys = list(paramiko.Transport._preferred_keys)
        orig_preferred_kex = tuple(paramiko.Transport._preferred_kex)
        orig_key_info = dict(paramiko.Transport._key_info)
        orig_kex_info = dict(paramiko.Transport._kex_info)

        logger.warning(
            "Legacy SSH algorithm exception active for device '%s' (%s): ssh-rsa, diffie-hellman-group14-sha1. Deprecation scheduled.",
            context.hostname,
            context.host,
        )

        try:
            # 1. Enable legacy ssh-rsa host key negotiation for older Ruijie hardware
            if "ssh-rsa" not in RSAKey.HASHES:
                RSAKey.HASHES["ssh-rsa"] = hashes.SHA1
            if "ssh-rsa" not in paramiko.Transport._key_info:
                paramiko.Transport._key_info["ssh-rsa"] = RSAKey
            if "ssh-rsa" not in paramiko.Transport._preferred_keys:
                paramiko.Transport._preferred_keys = list(paramiko.Transport._preferred_keys) + ["ssh-rsa"]

            # 2. Register legacy SHA1 Key Exchange algorithms required by Ruijie switches
            class KexGroup14SHA1(KexGroup14SHA256):
                name = "diffie-hellman-group14-sha1"
                hash_algo = hashlib.sha1

            class KexGexSHA1(KexGexSHA256):
                name = "diffie-hellman-group-exchange-sha1"
                hash_algo = hashlib.sha1

            paramiko.Transport._kex_info["diffie-hellman-group14-sha1"] = KexGroup14SHA1
            paramiko.Transport._kex_info["diffie-hellman-group-exchange-sha1"] = KexGexSHA1

            paramiko.Transport._preferred_kex = tuple(
                list(paramiko.Transport._preferred_kex)
                + [
                    k
                    for k in ("diffie-hellman-group14-sha1", "diffie-hellman-group-exchange-sha1")
                    if k not in paramiko.Transport._preferred_kex
                ]
            )

            # 3. Establish base SSH connection
            super().connect(context)
        finally:
            # Restore process-wide Paramiko preferences immediately to avoid lowering security posture for subsequent connections
            paramiko.Transport._preferred_keys = orig_preferred_keys
            paramiko.Transport._preferred_kex = orig_preferred_kex
            paramiko.Transport._key_info = orig_key_info
            paramiko.Transport._kex_info = orig_kex_info


        # 4. Enter privilege mode (enable) with secret password
        if self._connection is not None:
            if not self._connection.check_enable_mode():
                if not context.enable_password:
                    raise DriverConfigurationError(
                        "Ruijie Switch requires an enable secret password, but NETWORK_SSH_ENABLE_PASSWORD is not configured."
                    )
                self._connection.enable()

    def get_connection_parameters(
        self,
        context: DeviceConnectionContext,
    ) -> dict[str, Any]:
        params = super().get_connection_parameters(context)
        params["port"] = self.default_port
        if not context.enable_password:
            raise DriverConfigurationError(
                "Ruijie Switch requires an enable secret password, but NETWORK_SSH_ENABLE_PASSWORD is not configured."
            )
        params["secret"] = context.enable_password
        return params

    def collect_config(self) -> CollectedConfig:
        raw_output = self.send_command(self.export_command)
        return CollectedConfig(
            text=raw_output,
            extension=self.metadata.output_extension,
            filename="config.txt",
            encoding="utf-8",
        )

    def normalize_config(self, collected: CollectedConfig) -> str:
        text = collected.text

        # 1. Normalize line endings to LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Strip volatile Ruijie lines such as generation headers and timestamps
        text = re.sub(r"^Building configuration\.+\n?", "", text, flags=re.MULTILINE)
        text = re.sub(
            r"^Current configuration\s*:\s*\d+\s*bytes\n?",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        text = re.sub(
            r"^!\s*Time:\s*.*\n?",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # 3. Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]

        # 4. Remove leading and trailing empty lines
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
            raise DriverValidationError("Collected Ruijie Switch configuration is empty.")

        if len(trimmed) < 50:
            raise DriverValidationError(
                f"Ruijie Switch configuration is too short ({len(trimmed)} bytes)."
            )

        lower = trimmed.lower()
        cli_errors = [
            "invalid input detected",
            "incomplete command",
            "ambiguous command",
            "% unknown command",
            "error: ",
            "permission denied",
        ]
        for error in cli_errors:
            if error in lower:
                raise DriverValidationError(
                    f"Ruijie output contains CLI error message: '{error}'"
                )
