from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.database import get_db
from app.dependencies import (
    AuthContext,
    get_current_context,
    require_admin,
    require_admin_csrf,
)
from app.models.config_object import ConfigObject
from app.models.device import Device
from app.models.snapshot import Snapshot
from app.models.storage_repository import StorageRepository
from app.services.s3_service import S3Service, S3ServiceError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["snapshots"])


def _serialize_snapshot(snapshot: Snapshot, is_admin: bool, active_repo_id: uuid.UUID | None = None) -> dict[str, Any]:
    obj = snapshot.config_object
    is_storage_active = (active_repo_id is not None) and (
        snapshot.repository_id == active_repo_id if snapshot.repository_id else True
    )
    can_download = (
        is_admin
        and is_storage_active
        and snapshot.is_retained
        and (obj.storage_status == "available" if obj else False)
    )
    return {
        "id": snapshot.id,
        "device_id": snapshot.device_id,
        "backup_job_id": str(snapshot.backup_job_id),
        "captured_at": snapshot.captured_at.isoformat(),
        "change_status": snapshot.change_status,
        "retention_policy_at_capture": snapshot.retention_policy_at_capture,
        "retention_marks": [
            getattr(mark, "mark_type", getattr(mark, "retention_mark", getattr(mark, "tier", str(mark))))
            for mark in snapshot.retention_marks
        ] if snapshot.retention_marks else [],
        "display_filename": snapshot.display_filename,
        "is_retained": snapshot.is_retained,
        "expired_at": (
            snapshot.expired_at.isoformat() if snapshot.expired_at else None
        ),
        "object": {
            "id": obj.id,
            "size_bytes": obj.size_bytes,
            "content_sha256": obj.content_sha256,
            "object_sha256": obj.object_sha256,
            "storage_status": obj.storage_status,
            "uploaded_at": (
                obj.uploaded_at.isoformat() if obj.uploaded_at else None
            ),
            "verified_at": (
                obj.verified_at.isoformat() if obj.verified_at else None
            ),
        } if obj else None,
        "download_available": can_download,
    }



@router.get("/devices/{device_id}/snapshots")
def list_device_snapshots(
    device_id: int,
    retained_only: bool = Query(default=True),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if device is None:
        raise AppError(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message="Device not found.",
        )

    stmt = (
        select(Snapshot)
        .options(
            selectinload(Snapshot.config_object),
            selectinload(Snapshot.retention_marks),
        )
        .where(Snapshot.device_id == device_id)
    )

    active_repo = db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
    if not active_repo:
        return {
            "data": {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }
        }
    stmt = stmt.where(Snapshot.repository_id == active_repo.id)

    if retained_only:
        stmt = stmt.where(Snapshot.is_retained == True)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Snapshot.display_filename.ilike(search_pattern),
                Snapshot.change_status.ilike(search_pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    stmt = stmt.order_by(Snapshot.captured_at.desc()).offset(offset).limit(limit)
    snapshots = db.scalars(stmt).all()

    active_repo = db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
    active_repo_id = active_repo.id if active_repo else None

    is_admin = (context.user.role == "admin")
    return {
        "data": {
            "items": [_serialize_snapshot(s, is_admin, active_repo_id) for s in snapshots],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }



@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: int,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Snapshot)
        .options(
            selectinload(Snapshot.config_object),
            selectinload(Snapshot.retention_marks),
        )
        .where(Snapshot.id == snapshot_id)
    )
    snapshot = db.scalar(stmt)
    if snapshot is None:
        raise AppError(
            status_code=404,
            code="SNAPSHOT_NOT_FOUND",
            message="Snapshot not found.",
        )

    active_repo = db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
    active_repo_id = active_repo.id if active_repo else None

    is_admin = (context.user.role == "admin")
    return {"data": _serialize_snapshot(snapshot, is_admin, active_repo_id)}


@router.get("/snapshots/{snapshot_id}/download")
def download_snapshot(
    snapshot_id: int,
    context: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Snapshot)
        .options(selectinload(Snapshot.config_object))
        .where(Snapshot.id == snapshot_id)
    )
    snapshot = db.scalar(stmt)
    if snapshot is None:
        raise AppError(
            status_code=404,
            code="SNAPSHOT_NOT_FOUND",
            message="Snapshot not found.",
        )

    # SEC-STORAGE: Ensure active S3 storage repository is mounted and matches
    active_repo = db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
    if not active_repo:
        raise AppError(
            status_code=503,
            code="STORAGE_DISCONNECTED",
            message="S3 storage is currently disconnected. Cannot download backup file while storage is unmounted.",
        )

    if snapshot.repository_id and snapshot.repository_id != active_repo.id:
        raise AppError(
            status_code=409,
            code="REPOSITORY_MISMATCH",
            message=f"Snapshot belongs to repository '{snapshot.repository_id}' which is not currently active.",
        )

    if not snapshot.is_retained:
        raise AppError(
            status_code=410,
            code="SNAPSHOT_OBJECT_EXPIRED",
            message="Snapshot retention has expired and object is no longer available.",
        )

    obj = snapshot.config_object
    if obj is None or obj.storage_status != "available":
        raise AppError(
            status_code=502,
            code="S3_OBJECT_UNAVAILABLE",
            message="Config object is not available in storage.",
        )

    s3_service = S3Service(repo_id=snapshot.repository_id)
    try:
        data = s3_service.get_config_object(obj.s3_key)
    except S3ServiceError as exc:
        logger.error("Failed to read/decrypt S3 object %s: %s", obj.s3_key, exc)
        exc_str = str(exc)
        if "integrity verification failed" in exc_str or "INTEGRITY_VERIFICATION_FAILED" in exc_str:
            raise AppError(
                status_code=500,
                code="INTEGRITY_VERIFICATION_FAILED",
                message="Integrity check failed: configuration HMAC mismatch or payload corruption detected.",
            ) from exc
        if "decryption failed" in exc_str or "DECRYPTION_FAILED" in exc_str:
            raise AppError(
                status_code=500,
                code="PAYLOAD_DECRYPTION_FAILED",
                message="Payload decryption failed: invalid master key or corrupt envelope.",
            ) from exc
        raise AppError(
            status_code=502,
            code="S3_OBJECT_UNAVAILABLE",
            message=f"Unable to retrieve configuration object from Ceph S3: {exc}",
        ) from exc

    downloaded_sha256 = hashlib.sha256(data).hexdigest()
    if downloaded_sha256 != obj.object_sha256:
        logger.error(
            "Checksum mismatch for snapshot %s: expected %s, got %s",
            snapshot.id,
            obj.object_sha256,
            downloaded_sha256,
        )
        raise AppError(
            status_code=500,
            code="OBJECT_CHECKSUM_MISMATCH",
            message="Integrity check failed: configuration checksum mismatch.",
        )

    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{snapshot.display_filename}"',
            "X-Content-SHA256": obj.object_sha256,
        },
    )


@router.post("/snapshots/retention/run")
def trigger_retention_policy(
    dry_run: bool = Query(default=False),
    context: AuthContext = Depends(require_admin_csrf),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Executes or simulates the backup retention policy across repositories.
    Supports dry-run preview to inspect retention and expiration decisions.
    """
    from app.services.retention_service import RetentionService
    svc = RetentionService(db)
    summary = svc.run_retention_policy(dry_run=dry_run)
    return {"data": summary}

