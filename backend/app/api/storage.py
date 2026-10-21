from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, require_admin_csrf
from app.services.storage_repository_service import StorageRepositoryService

router = APIRouter(prefix="/storage", tags=["storage"])


class S3TestRequest(BaseModel):
    endpoint: str = Field(..., min_length=1)
    bucket: str = Field(..., min_length=1)
    access_key: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=1)
    secure: bool = True


class S3InitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    endpoint: str = Field(..., min_length=1)
    bucket: str = Field(..., min_length=1)
    access_key: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=1)
    secure: bool = True
    master_password: str = Field(..., min_length=8)


class S3UnlockRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    endpoint: str = Field(..., min_length=1)
    bucket: str = Field(..., min_length=1)
    access_key: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=1)
    secure: bool = True
    master_password: str = Field(..., min_length=1)


class S3RotatePasswordRequest(BaseModel):
    current_master_password: str = Field(..., min_length=1)
    new_master_password: str = Field(..., min_length=8)


@router.post("/test")
def test_s3_connection(
    payload: S3TestRequest,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    res = svc.test_connection(
        endpoint=payload.endpoint,
        bucket=payload.bucket,
        access_key=payload.access_key,
        secret_key=payload.secret_key,
        secure=payload.secure,
    )
    return {"data": res}


@router.get("/repositories")
def list_repositories(
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    items = svc.list_repositories()
    return {"data": items}


@router.get("/active")
def get_active_repository(
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    repo = svc.get_active_repository()
    return {"data": repo or {}}


@router.post("/repositories/init")
def initialize_repository(
    payload: S3InitRequest,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    repo = svc.initialize_repository(
        name=payload.name,
        endpoint=payload.endpoint,
        bucket=payload.bucket,
        access_key=payload.access_key,
        secret_key=payload.secret_key,
        secure=payload.secure,
        master_password=payload.master_password,
    )
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="INFO",
        event_type="STORAGE_REPOSITORY_INITIALIZED",
        message=f"S3 repository '{repo.name}' (bucket: {repo.bucket}) initialized and activated by {_ctx.user.username}.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint="/storage/repositories/init",
        details={"repo_id": str(repo.id), "name": repo.name, "bucket": repo.bucket},
    )
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' initialized and activated successfully.",
            "repo_id": str(repo.id),
            "name": repo.name,
        }
    }


@router.post("/repositories/unlock")
def unlock_repository(
    payload: S3UnlockRequest,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    repo = svc.unlock_and_activate(
        name=payload.name,
        endpoint=payload.endpoint,
        bucket=payload.bucket,
        access_key=payload.access_key,
        secret_key=payload.secret_key,
        secure=payload.secure,
        master_password=payload.master_password,
    )
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="INFO",
        event_type="STORAGE_REPOSITORY_UNLOCKED",
        message=f"S3 repository '{repo.name}' (bucket: {repo.bucket}) unlocked and mounted by {_ctx.user.username}.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint="/storage/repositories/unlock",
        details={"repo_id": str(repo.id), "name": repo.name, "bucket": repo.bucket},
    )
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' unlocked and activated successfully.",
            "repo_id": str(repo.id),
            "name": repo.name,
        }
    }


@router.post("/repositories/{repo_id}/activate")
def activate_repository(
    repo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    repo = svc.activate_repository(repo_id)
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="INFO",
        event_type="STORAGE_MOUNTED",
        message=f"S3 storage repository '{repo.name}' activated and mounted.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint=f"/storage/repositories/{repo_id}",
        details={"repo_id": str(repo.id), "name": repo.name},
    )
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' is now active.",
            "repo_id": str(repo.id),
            "name": repo.name,
        }
    }


@router.delete("/repositories/{repo_id}")
def delete_repository(
    repo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    res = svc.delete_repository(repo_id)
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="WARNING",
        event_type="STORAGE_DELETED",
        message=f"S3 storage repository #{repo_id} deleted by {_ctx.user.username}.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint=f"/storage/repositories/{repo_id}",
        details={"repo_id": str(repo_id)},
    )
    return {"data": res}


@router.post("/disconnect")
def disconnect_repository(
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    svc.deactivate_all()
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="WARNING",
        event_type="STORAGE_DISCONNECTED",
        message=f"S3 storage connection disconnected by {_ctx.user.username}.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint="/storage/disconnect",
    )
    return {
        "data": {
            "success": True,
            "message": "S3 storage disconnected successfully.",
        }
    }


@router.post("/repositories/{repo_id}/rotate-password")
def rotate_repository_password(
    repo_id: uuid.UUID,
    payload: S3RotatePasswordRequest,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    repo = svc.rotate_repository_password(
        repo_id,
        current_master_password=payload.current_master_password,
        new_master_password=payload.new_master_password,
    )
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="STORAGE",
        severity="WARNING",
        event_type="STORAGE_PASSWORD_ROTATED",
        message=f"Master password rotated and manifest re-encrypted for repository '{repo.name}'.",
        source_ip=_ctx.source_ip,
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint=f"/storage/repositories/{repo_id}/rotate-password",
        details={"repo_id": str(repo.id), "name": repo.name},
    )
    return {
        "data": {
            "success": True,
            "message": f"Master password for repository '{repo.name}' rotated and manifest re-encrypted successfully.",
            "repo_id": str(repo.id),
        }
    }
