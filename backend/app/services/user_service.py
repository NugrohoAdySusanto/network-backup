from __future__ import annotations

from app.core.errors import AppError
from app.core.security import hash_password, normalize_username
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def create_user(
        self,
        *,
        username: str,
        password: str,
        role: str,
        email: str | None = None,
    ) -> User:
        username = normalize_username(username)
        if self.repository.get_by_username(username) is not None:
            raise AppError(
                status_code=409,
                code="USERNAME_ALREADY_EXISTS",
                message="Username already exists.",
            )

        clean_email = email.strip().lower() if email and email.strip() else None
        if clean_email and self.repository.get_by_email(clean_email) is not None:
            raise AppError(
                status_code=409,
                code="EMAIL_ALREADY_EXISTS",
                message="Email address already registered.",
            )

        role = role.strip().lower()
        if role == "visitor":
            role = "viewer"
        if role not in {"admin", "viewer"}:
            raise AppError(
                status_code=422,
                code="INVALID_ROLE",
                message="Role must be admin or viewer.",
            )

        user = self.repository.create(
            username=username,
            email=clean_email,
            password_hash=hash_password(password),
            role=role,
        )
        self.repository.commit()
        self.repository.refresh(user)
        return user

    def deactivate_user(self, *, target_user_id: int, current_user_id: int) -> None:
        user = self.repository.get_by_id(target_user_id)
        if user is None:
            raise AppError(
                status_code=404,
                code="USER_NOT_FOUND",
                message="User not found.",
            )

        if user.id == current_user_id:
            raise AppError(
                status_code=400,
                code="CANNOT_DEACTIVATE_SELF",
                message="You cannot deactivate your own account.",
            )

        if user.role == "admin" and user.is_active:
            if self.repository.count_active_admins() <= 1:
                raise AppError(
                    status_code=409,
                    code="CANNOT_DEACTIVATE_LAST_ADMIN",
                    message="The last active Admin cannot be deactivated.",
                )

        user.is_active = False
        self.repository.commit()
