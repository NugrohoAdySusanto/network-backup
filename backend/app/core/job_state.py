
from __future__ import annotations

from app.core.enums import BackupJobState


TERMINAL_STATES = {
    BackupJobState.SUCCESS_CHANGED.value,
    BackupJobState.SUCCESS_NO_CHANGE.value,
    BackupJobState.SKIPPED_DEVICE_DOWN.value,
    BackupJobState.SKIPPED_STATUS_UNKNOWN.value,
    BackupJobState.FAILED.value,
}

ACTIVE_STATES = {
    BackupJobState.QUEUED.value,
    BackupJobState.PRECHECKING_ZABBIX.value,
    BackupJobState.CONNECTING.value,
    BackupJobState.COLLECTING.value,
    BackupJobState.NORMALIZING.value,
    BackupJobState.VALIDATING.value,
    BackupJobState.HASHING.value,
    BackupJobState.UPLOADING.value,
    BackupJobState.VERIFYING.value,
    BackupJobState.RETRYING.value,
}

_NORMAL_FLOW = {
    BackupJobState.QUEUED.value: {
        BackupJobState.PRECHECKING_ZABBIX.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.PRECHECKING_ZABBIX.value: {
        BackupJobState.CONNECTING.value,
        BackupJobState.SKIPPED_DEVICE_DOWN.value,
        BackupJobState.SKIPPED_STATUS_UNKNOWN.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.CONNECTING.value: {
        BackupJobState.COLLECTING.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.COLLECTING.value: {
        BackupJobState.NORMALIZING.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.NORMALIZING.value: {
        BackupJobState.VALIDATING.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.VALIDATING.value: {
        BackupJobState.HASHING.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.HASHING.value: {
        BackupJobState.UPLOADING.value,
        BackupJobState.SUCCESS_NO_CHANGE.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.UPLOADING.value: {
        BackupJobState.VERIFYING.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.VERIFYING.value: {
        BackupJobState.SUCCESS_CHANGED.value,
        BackupJobState.RETRYING.value,
        BackupJobState.FAILED.value,
    },
    BackupJobState.RETRYING.value: {
        BackupJobState.PRECHECKING_ZABBIX.value,
        BackupJobState.FAILED.value,
    },
}


class InvalidJobTransitionError(RuntimeError):
    pass


def validate_transition(current: str, target: str) -> None:
    if current == target:
        return
    if current in TERMINAL_STATES:
        raise InvalidJobTransitionError(
            f"Terminal state {current} cannot transition to {target}."
        )

    allowed = _NORMAL_FLOW.get(current, set())
    if target not in allowed:
        raise InvalidJobTransitionError(
            f"Invalid backup-job transition: {current} -> {target}."
        )
