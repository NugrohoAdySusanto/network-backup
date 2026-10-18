from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> User | None:
        if not email:
            return None
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return self.db.scalar(stmt)

    def get_by_identifier(self, identifier: str) -> User | None:
        if not identifier:
            return None
        val = identifier.strip()
        stmt = select(User).where((User.username == val) | (func.lower(User.email) == val.lower()))
        return self.db.scalar(stmt)

    def list_users(
        self,
        *,
        limit: int,
        offset: int,
        active_only: bool = True,
    ) -> tuple[list[User], int]:
        base_stmt = select(User)
        if active_only:
            base_stmt = base_stmt.where(User.is_active.is_(True))
        total = self.db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
        stmt = base_stmt.order_by(User.id.asc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all()), int(total)

    def count_active_admins(self) -> int:
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active.is_(True))
        )
        return int(self.db.scalar(stmt) or 0)

    def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        email: str | None = None,
    ) -> User:
        user = User(
            username=username,
            email=email.strip().lower() if email and email.strip() else None,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, user: User) -> None:
        self.db.refresh(user)
