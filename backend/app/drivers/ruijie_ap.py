from __future__ import annotations

import re

from app.drivers.base import (
    CollectedConfig,
    DeviceConnectionContext,
    DriverMetadata,
    DriverValidationError,
)
from app.drivers.netmiko_base import BaseNetmikoDriver


class RuijieAPDriver(BaseNetmikoDriver):
    metadata = DriverMetadata(
        key="ruijie-ap",
        label="Ruijie AP Driver",
        transport="ssh",
        implementation="netmiko",
        output_extension="text",
        vendor_hint="Ruijie Networks",
        model_hint="AP",
    )

    netmiko_device_type = "ruijie_os"
    export_command = "show running-config"

    def connect(self, context: DeviceConnectionContext) -> None:
        import paramiko
        from paramiko.rsakey import RSAKey
        from cryptography.hazmat.primitives import hashes

        # Enable legacy ssh-rsa host key negotiation for Ruijie AP devices
        if "ssh-rsa" not in RSAKey.HASHES:
            RSAKey.HASHES["ssh-rsa"] = hashes.SHA1
        if "ssh-rsa" not in paramiko.Transport._key_info:
            paramiko.Transport._key_info["ssh-rsa"] = RSAKey
        if "ssh-rsa" not in paramiko.Transport._preferred_keys:
            paramiko.Transport._preferred_keys = list(paramiko.Transport._preferred_keys) + ["ssh-rsa"]

        super().connect(context)

    def collect_config(self) -> CollectedConfig:
        raw_output = self.send_command(self.export_command)
        return CollectedConfig(
            text=raw_output,
            extension=self.metadata.output_extension,
            filename="config.text",
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

        # 3. Strip trailing CLI prompt if captured (e.g. MKK-HQ_AP-01#)
        text = re.sub(r"\n?[a-zA-Z0-9_\-]+[#>]\s*$", "", text.strip())

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
            raise DriverValidationError("Collected Ruijie AP configuration is empty.")

        if len(trimmed) < 50:
            raise DriverValidationError(
                f"Ruijie AP configuration is too short ({len(trimmed)} bytes)."
            )

        lower = trimmed.lower()
        cli_errors = [
            "invalid input detected",
            "incomplete command",
            "ambiguous command",
            "% unknown command",
            "error: ",
            "permission denied",
            "connection refused",
        ]
        for error in cli_errors:
            if error in lower:
                raise DriverValidationError(
                    f"Ruijie AP output contains CLI error message: '{error}'"
                )

        if "hostname" not in lower and "version" not in lower:
            raise DriverValidationError(
                "Ruijie AP configuration lacks expected signature ('hostname' or 'version')."
            )
