from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Depends, Header

from app.config import settings
from app.core.errors import AppError
from app.core.security import constant_time_equal
from app.core.session import SessionData, session_store
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class AuthContext:
    user: User
    session_id: str
    session: SessionData


def get_current_context(
    session_id: str | None = Cookie(
        default=None,
        alias=settings.session_cookie_name,
    ),
    db=Depends(get_db),
) -> AuthContext:
    if not session_id:
        raise AppError(
            status_code=401,
            code="SESSION_INVALID",
            message="Authentication required.",
        )

    session = session_store.get(session_id)
    if session is None:
        raise AppError(
            status_code=401,
            code="SESSION_INVALID",
            message="Session is invalid or expired.",
        )

    repository = UserRepository(db)
    user = repository.get_by_id(session.user_id)

    if user is None or not user.is_active:
        session_store.delete(session_id)
        raise AppError(
            status_code=401,
            code="SESSION_INVALID",
            message="Session is invalid or expired.",
        )

    session_store.touch(session_id, session.remember_me)
    return AuthContext(
        user=user,
        session_id=session_id,
        session=session,
    )


def get_current_user(
    context: AuthContext = Depends(get_current_context),
) -> User:
    return context.user


def require_admin(
    context: AuthContext = Depends(get_current_context),
) -> AuthContext:
    if context.user.role != "admin":
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Admin permission is required.",
        )
    return context


def require_csrf(
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    context: AuthContext = Depends(get_current_context),
) -> AuthContext:
    if not csrf_token or not constant_time_equal(
        csrf_token,
        context.session.csrf_token,
    ):
        raise AppError(
            status_code=403,
            code="CSRF_INVALID",
            message="CSRF token is invalid.",
        )
    return context


def require_admin_csrf(
    context: AuthContext = Depends(require_csrf),
) -> AuthContext:
    if context.user.role != "admin":
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Admin permission is required.",
        )
    return context
