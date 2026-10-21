from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import AppError
from app.core.security import (
    hash_password,
    needs_rehash,
    normalize_username,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def authenticate(self, *, username: str, password: str) -> User:
        normalized = normalize_username(username)
        user = self.repository.get_by_username(normalized)

        if user is None or not verify_password(user.password_hash, password):
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Invalid username or password.",
            )

        if not user.is_active:
            raise AppError(
                status_code=403,
                code="USER_INACTIVE",
                message="This account is inactive.",
            )

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        user.last_login_at = datetime.now(timezone.utc)
        self.repository.commit()
        self.repository.refresh(user)
        return user

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        if new_password != confirm_password:
            raise AppError(
                status_code=400,
                code="PASSWORD_CONFIRMATION_MISMATCH",
                message="New password confirmation does not match.",
            )

        if not verify_password(user.password_hash, current_password):
            raise AppError(
                status_code=401,
                code="CURRENT_PASSWORD_INVALID",
                message="Current password is invalid.",
            )

        user.password_hash = hash_password(new_password)
        self.repository.commit()

    def request_password_reset(self, *, email: str) -> None:
        import hashlib
        import secrets
        from app.core.session import session_store
        from app.services.email_service import email_service

        clean_email = email.strip().lower() if email else ""
        if not clean_email or "@" not in clean_email:
            return

        user = self.repository.get_by_email(clean_email)
        if user is None or not user.is_active or not user.email:
            # Timing-safe return to prevent user enumeration
            return

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Store in Redis with TTL 15 minutes (900 seconds)
        session_store._redis.setex(f"pw-reset:{token_hash}", 900, str(user.id))

        try:
            email_service.send_password_reset_email(
                to_email=user.email,
                username=user.username,
                reset_token=raw_token,
            )
        except Exception as exc:
            session_store._redis.delete(f"pw-reset:{token_hash}")
            raise AppError(
                status_code=500,
                code="EMAIL_SENDING_FAILED",
                message=f"Failed to send password reset email: {exc}",
            ) from exc

    def complete_password_reset(
        self,
        *,
        token: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        import hashlib
        from app.core.security import validate_password_policy
        from app.core.session import session_store

        if not token or len(token) < 16:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Password reset link is invalid or has expired.",
            )

        if new_password != confirm_password:
            raise AppError(
                status_code=400,
                code="PASSWORD_CONFIRMATION_MISMATCH",
                message="New password confirmation does not match.",
            )

        validate_password_policy(new_password)

        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        user_id_raw = session_store._redis.get(f"pw-reset:{token_hash}")
        if not user_id_raw:
            raise AppError(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Password reset link is invalid or has expired.",
            )

        user = self.repository.get_by_id(int(user_id_raw))
        if user is None or not user.is_active:
            raise AppError(
                status_code=400,
                code="USER_INACTIVE",
                message="User account is inactive or not found.",
            )

        user.password_hash = hash_password(new_password)
        self.repository.commit()
        session_store._redis.delete(f"pw-reset:{token_hash}")
