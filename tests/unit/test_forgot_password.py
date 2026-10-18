"""
Unit tests for Forgot Password & Reset Password workflow.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.auth_service import AuthService


def test_forgot_password_unknown_identifier_is_safe():
    repo = MagicMock()
    repo.get_by_email.return_value = None
    service = AuthService(repo)

    # Unknown user should return gracefully without raising error (prevent user enumeration)
    service.request_password_reset(email="nonexistent_user_999@test.com")


def test_forgot_password_and_reset_flow():
    mock_redis = {}

    def redis_setex(key, ttl, value):
        mock_redis[key] = value

    def redis_get(key):
        return mock_redis.get(key)

    def redis_delete(key):
        mock_redis.pop(key, None)

    fake_user = User(
        id=42,
        username="noc_operator",
        email="noc_operator@makuku.co.id",
        password_hash=hash_password("OldPassword123!"),
        role="viewer",
        is_active=True,
    )

    repo = MagicMock()
    repo.get_by_email.return_value = fake_user
    repo.get_by_id.return_value = fake_user
    service = AuthService(repo)

    captured_token = None

    def fake_send_email(*, to_email, username, reset_token):
        nonlocal captured_token
        captured_token = reset_token
        return True

    with patch("app.core.session.session_store._redis.setex", side_effect=redis_setex), \
         patch("app.core.session.session_store._redis.get", side_effect=redis_get), \
         patch("app.core.session.session_store._redis.delete", side_effect=redis_delete), \
         patch("app.services.email_service.email_service.send_password_reset_email", side_effect=fake_send_email):

        # 1. Request password reset with email
        service.request_password_reset(email="noc_operator@makuku.co.id")
        assert captured_token is not None

        # 2. Mismatched passwords should raise error
        with pytest.raises(AppError) as exc_info:
            service.complete_password_reset(
                token=captured_token,
                new_password="NewSecurePassword123!",
                confirm_password="MismatchPassword123!",
            )
        assert exc_info.value.code == "PASSWORD_CONFIRMATION_MISMATCH"

        # 3. Invalid token should raise error
        with pytest.raises(AppError) as exc_info:
            service.complete_password_reset(
                token="wrong_token_1234567890",
                new_password="NewSecurePassword123!",
                confirm_password="NewSecurePassword123!",
            )
        assert exc_info.value.code == "INVALID_RESET_TOKEN"

        # 4. Successful reset
        service.complete_password_reset(
            token=captured_token,
            new_password="NewSecurePassword123!",
            confirm_password="NewSecurePassword123!",
        )

        # Verify password changed
        assert verify_password(fake_user.password_hash, "NewSecurePassword123!") is True
        assert verify_password(fake_user.password_hash, "OldPassword123!") is False

        # 5. Token is consumed, second reset fails
        with pytest.raises(AppError) as exc_info:
            service.complete_password_reset(
                token=captured_token,
                new_password="AnotherPassword123!",
                confirm_password="AnotherPassword123!",
            )
        assert exc_info.value.code == "INVALID_RESET_TOKEN"
