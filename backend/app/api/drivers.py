from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthContext, get_current_context, require_admin_csrf
from app.services.driver_management_service import DriverManagementService

router = APIRouter(prefix="/drivers", tags=["drivers"])


class CustomDriverPayload(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    label: str = Field(..., min_length=2, max_length=128)
    vendor_hint: str = Field(..., min_length=1, max_length=128)
    model_hint: str = Field(..., min_length=1, max_length=128)
    transport: str = Field("ssh", max_length=32)
    default_port: int = Field(22, ge=1, le=65535)
    connect_timeout: int = Field(15, ge=1, le=120)
    command_timeout: int = Field(60, ge=1, le=300)
    need_enable: bool = False
    enable_command: str = Field("enable", max_length=64)
    enable_prompt_pattern: str = Field(r"[#$]", max_length=64)
    disable_paging_command: str | None = None
    paging_mode: str = Field("none", max_length=32)
    backup_command: str = Field("show running-config", max_length=255)
    output_extension: str = Field("txt", max_length=16)
    strip_patterns: list[str] = Field(default_factory=list)
    validation_min_length: int = Field(30, ge=1)
    validation_required_keyword: str | None = None
    is_active: bool = True


class DriverTestPayload(BaseModel):
    driver_data: dict[str, Any]
    device_id: int


@router.get("")
def list_drivers(
    db: Session = Depends(get_db),
    _: AuthContext = Depends(get_current_context),
) -> dict[str, Any]:
    svc = DriverManagementService(db)
    items = svc.list_drivers()
    return {
        "data": {
            "items": items,
        }
    }


@router.post("/custom")
def create_custom_driver(
    payload: CustomDriverPayload,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = DriverManagementService(db)
    driver = svc.create_custom_driver(payload.model_dump())
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="INFO",
        event_type="WORKER_CREATED",
        message=f"Backup worker '{driver.label}' ({driver.key}) created by {_ctx.user.username}.",
        source_ip=getattr(_ctx, "source_ip", None),
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint="/drivers/custom",
        details={"key": driver.key, "label": driver.label},
    )
    return {
        "data": {
            "success": True,
            "message": f"Backup worker '{driver.label}' added successfully.",
            "key": driver.key,
        }
    }


@router.put("/custom/{key}")
def update_custom_driver(
    key: str,
    payload: CustomDriverPayload,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = DriverManagementService(db)
    driver = svc.update_custom_driver(key, payload.model_dump())
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="INFO",
        event_type="WORKER_UPDATED",
        message=f"Backup worker '{driver.label}' ({driver.key}) updated by {_ctx.user.username}.",
        source_ip=getattr(_ctx, "source_ip", None),
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint=f"/drivers/custom/{key}",
        details={"key": driver.key, "label": driver.label},
    )
    return {
        "data": {
            "success": True,
            "message": f"Backup worker '{driver.label}' updated successfully.",
            "key": driver.key,
        }
    }


@router.delete("/custom/{key}")
def delete_custom_driver(
    key: str,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = DriverManagementService(db)
    svc.delete_custom_driver(key)
    from app.services.audit_log_service import AuditLogService
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="WARNING",
        event_type="WORKER_DELETED",
        message=f"Backup worker '{key}' deleted by {_ctx.user.username}.",
        source_ip=getattr(_ctx, "source_ip", None),
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint=f"/drivers/custom/{key}",
        details={"key": key},
    )
    return {
        "data": {
            "success": True,
            "message": f"Backup worker '{key}' deleted successfully.",
        }
    }


@router.post("/test")
def test_custom_driver(
    payload: DriverTestPayload,
    db: Session = Depends(get_db),
    _ctx=Depends(require_admin_csrf),
) -> dict[str, Any]:
    svc = DriverManagementService(db)
    res = svc.test_driver(payload.driver_data, payload.device_id)
    from app.services.audit_log_service import AuditLogService
    success = bool(res.get("success"))
    AuditLogService.record_event_standalone(
        category="AUDIT",
        severity="INFO" if success else "WARNING",
        event_type="WORKER_TESTED",
        message=f"Backup worker test connection on device #{payload.device_id} {'succeeded' if success else 'failed'}.",
        source_ip=getattr(_ctx, "source_ip", None),
        user_id=_ctx.user.id,
        username=_ctx.user.username,
        endpoint="/drivers/test",
        details={
            "device_id": payload.device_id,
            "success": success,
            "error_details": res.get("error_details"),
        },
    )
    return {"data": res}
