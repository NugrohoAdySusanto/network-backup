from __future__ import annotations

import re

from app.drivers.base import (
    CollectedConfig,
    DriverMetadata,
    DriverValidationError,
)
from app.drivers.netmiko_base import BaseNetmikoDriver


class MikrotikRouterOSDriver(BaseNetmikoDriver):
    metadata = DriverMetadata(
        key="mikrotik-routeros",
        label="Mikrotik RouterOS Driver",
        transport="ssh",
        implementation="netmiko",
        output_extension="rsc",
        vendor_hint="Mikrotik",
        model_hint="RouterOS",
    )

    netmiko_device_type = "mikrotik_routeros"
    export_command = "/export compact"

    def collect_config(self) -> CollectedConfig:
        raw_output = self.send_command(self.export_command)
        return CollectedConfig(
            text=raw_output,
            extension=self.metadata.output_extension,
            encoding="utf-8",
        )

    def normalize_config(self, collected: CollectedConfig) -> str:
        text = collected.text

        # 1. Normalize line endings to LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Strip volatile RouterOS export header containing execution timestamp:
        # e.g.: "# oct/04/2026 17:19:39 by RouterOS 6.49.20"
        text = re.sub(
            r"^#\s+[a-zA-Z]{3}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+by\s+RouterOS[^\n]*\n?",
            "",
            text,
            flags=re.MULTILINE,
        )

        # 3. Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]

        # 4. Remove leading and trailing empty lines for a deterministic document
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
            raise DriverValidationError("Collected RouterOS configuration is empty.")

        if len(trimmed) < 50:
            raise DriverValidationError(
                f"RouterOS configuration is too short ({len(trimmed)} bytes)."
            )

        # Check for known RouterOS CLI error strings
        lower = trimmed.lower()
        cli_errors = [
            "bad command name",
            "syntax error",
            "failure:",
            "interrupted",
            "ambiguous value",
            "invalid internal item number",
        ]
        for error in cli_errors:
            if error in lower:
                raise DriverValidationError(
                    f"RouterOS output contains CLI error message: '{error}'"
                )

        # Valid RouterOS compact export must contain sections starting with '/' or '#'
        has_section = any(
            line.startswith("/") or line.startswith("#")
            for line in trimmed.splitlines()
        )
        if not has_section:
            raise DriverValidationError(
                "Output does not appear to be a valid RouterOS configuration script."
            )
