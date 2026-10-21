from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthContext, require_admin, require_admin_csrf
from app.repositories.user_repository import UserRepository
from app.schemas.user import CreateUserRequest, UserPublic
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    include_inactive: bool = Query(default=False),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    repository = UserRepository(db)
    users, total = repository.list_users(
        limit=limit,
        offset=offset,
        active_only=not include_inactive,
    )
    return {
        "data": {
            "items": [
                UserPublic.model_validate(user).model_dump(mode="json")
                for user in users
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.post("", status_code=201)
def create_user(
    payload: CreateUserRequest,
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))
    user = service.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="SECURITY",
        severity="INFO",
        event_type="USER_CREATED",
        message=f"User account '{user.username}' (role: {user.role}) created by {context.user.username}.",
        source_ip=context.source_ip,
        user_id=context.user.id,
        username=context.user.username,
        endpoint="/users",
        details={"target_user_id": user.id, "target_username": user.username, "role": user.role},
    )
    return {
        "data": UserPublic.model_validate(user).model_dump(mode="json")
    }


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
) -> Response:
    service = UserService(UserRepository(db))
    service.deactivate_user(
        target_user_id=user_id,
        current_user_id=context.user.id,
    )
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="SECURITY",
        severity="WARNING",
        event_type="USER_DEACTIVATED",
        message=f"User account #{user_id} deactivated by {context.user.username}.",
        source_ip=context.source_ip,
        user_id=context.user.id,
        username=context.user.username,
        endpoint=f"/users/{user_id}",
        details={"target_user_id": user_id},
    )
    return Response(status_code=204)
