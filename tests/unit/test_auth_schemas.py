import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import CreateUserRequest


def test_create_user_normalizes_username_and_role() -> None:
    payload = CreateUserRequest(
        username="  NOC.Viewer  ",
        password="ExamplePass123!",
        role="VIEWER",
    )
    assert payload.username == "NOC.Viewer"
    assert payload.role == "viewer"


def test_invalid_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            username="user",
            password="ExamplePass123!",
            role="operator",
        )


def test_change_password_schema_preserves_confirmation_for_service_check() -> None:
    payload = ChangePasswordRequest(
        current_password="OldPass123!",
        new_password="NewPass123!",
        confirm_password="Different123!",
    )
    assert payload.new_password != payload.confirm_password
