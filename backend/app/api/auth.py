from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.core.session import session_store
from app.database import get_db
from app.dependencies import AuthContext, get_current_context, require_csrf
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(
    response: Response,
    *,
    session_id: str,
    remember_me: bool,
    ttl: int,
) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=ttl if remember_me else None,
    )


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    repository = UserRepository(db)
    service = AuthService(repository)
    user = service.authenticate(
        username=payload.username,
        password=payload.password,
    )

    session_id, session_data, ttl = session_store.create(
        user_id=user.id,
        remember_me=payload.remember_me,
    )
    _set_session_cookie(
        response,
        session_id=session_id,
        remember_me=payload.remember_me,
        ttl=ttl,
    )

    return {
        "data": {
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "csrf_token": session_data.csrf_token,
        }
    }


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    context: AuthContext = Depends(require_csrf),
) -> Response:
    session_store.delete(context.session_id)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.status_code = 204
    return response


@router.get("/me")
def me(
    context: AuthContext = Depends(get_current_context),
):
    return {
        "data": {
            "user": UserPublic.model_validate(context.user).model_dump(mode="json"),
            "csrf_token": context.session.csrf_token,
        }
    }


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    service = AuthService(UserRepository(db))
    service.change_password(
        user=context.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )

    return Response(status_code=204)


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(UserRepository(db))
    service.request_password_reset(email=payload.target_email)
    return {
        "data": {
            "message": "Jika alamat email tersebut terdaftar, tautan pemulihan telah dikirim ke email Anda."
        }
    }


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(UserRepository(db))
    service.complete_password_reset(
        token=payload.token,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )
    return {
        "data": {
            "message": "Password berhasil diubah. Silakan login dengan password baru Anda."
        }
    }
