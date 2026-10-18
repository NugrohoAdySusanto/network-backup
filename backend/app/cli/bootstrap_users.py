from __future__ import annotations

from app.config import settings
from app.database import new_session
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


def bootstrap_one(
    service: UserService,
    repository: UserRepository,
    *,
    username: str,
    password: str,
    role: str,
) -> None:
    if not password:
        print(f"SKIP {username}: password not configured")
        return

    existing = repository.get_by_username(username.strip().lower())
    if existing is not None:
        print(f"SKIP {username}: already exists")
        return

    user = service.create_user(
        username=username,
        password=password,
        role=role,
    )
    print(f"CREATED {user.username} ({user.role})")


def main() -> None:
    if not settings.bootstrap_users_enabled:
        print("Bootstrap users are disabled.")
        return

    with new_session() as db:
        repository = UserRepository(db)
        service = UserService(repository)

        bootstrap_one(
            service,
            repository,
            username=settings.bootstrap_admin_username,
            password=settings.bootstrap_admin_password,
            role="admin",
        )
        bootstrap_one(
            service,
            repository,
            username=settings.bootstrap_viewer_username,
            password=settings.bootstrap_viewer_password,
            role="viewer",
        )


if __name__ == "__main__":
    main()
