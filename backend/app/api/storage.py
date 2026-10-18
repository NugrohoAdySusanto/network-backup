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
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' berhasil diinisialisasi dan diaktifkan.",
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
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' berhasil dibuka kuncinya dan diaktifkan.",
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
    return {
        "data": {
            "success": True,
            "message": f"Repository '{repo.name}' sekarang aktif.",
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
    return {"data": res}


@router.post("/disconnect")
def disconnect_repository(
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = StorageRepositoryService(db)
    svc.deactivate_all()
    return {
        "data": {
            "success": True,
            "message": "Koneksi storage S3 berhasil diputuskan.",
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
    return {
        "data": {
            "success": True,
            "message": f"Master password untuk repository '{repo.name}' berhasil dirotasi dan manifest telah dire-enkripsi.",
            "repo_id": str(repo.id),
        }
    }
