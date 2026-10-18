
import pytest

from app.core.job_state import (
    InvalidJobTransitionError,
    validate_transition,
)


def test_valid_queue_to_precheck_transition() -> None:
    validate_transition("QUEUED", "PRECHECKING_ZABBIX")


def test_down_precheck_is_terminal_transition() -> None:
    validate_transition(
        "PRECHECKING_ZABBIX",
        "SKIPPED_DEVICE_DOWN",
    )


def test_terminal_state_cannot_transition() -> None:
    with pytest.raises(InvalidJobTransitionError):
        validate_transition(
            "SUCCESS_NO_CHANGE",
            "QUEUED",
        )


def test_invalid_jump_is_rejected() -> None:
    with pytest.raises(InvalidJobTransitionError):
        validate_transition(
            "QUEUED",
            "UPLOADING",
        )
