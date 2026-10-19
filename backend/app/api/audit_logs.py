from __future__ import annotations

from datetime import datetime, timezone
import logging
import math
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthContext, get_current_context
from app.models.audit_log import SystemAuditLog
from app.schemas.audit_log import AuditLogListResponse, AuditLogRead, AuditLogStatsResponse
from app.services.audit_export_service import AuditExportService
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

router = APIRouter(prefix="/logs", tags=["audit-logs"])


def _parse_datetime(dt_str: str | None, is_end: bool = False) -> datetime | None:
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=WIB)
        if is_end and len(dt_str) <= 10:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError:
        try:
            d = datetime.strptime(dt_str, "%Y-%m-%d")
            if is_end:
                d = d.replace(hour=23, minute=59, second=59, microsecond=999999)
            return d.replace(tzinfo=WIB)
        except ValueError:
            return None


@router.get("", response_model=dict[str, Any])
def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated audit and security logs with multi-parameter filtering.
    """
    dt_start = _parse_datetime(start_date, is_end=False)
    dt_end = _parse_datetime(end_date, is_end=True)

    items, total = AuditLogService.query_logs(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
        severity=severity,
        event_type=event_type,
        search=search,
        start_date=dt_start,
        end_date=dt_end,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "data": {
            "items": [AuditLogRead.model_validate(item).model_dump(mode="json") for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    }


@router.get("/stats", response_model=dict[str, Any])
def get_log_stats(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """
    Returns aggregate statistics and KPI metrics for dashboard cards.
    """
    dt_start = _parse_datetime(start_date, is_end=False)
    dt_end = _parse_datetime(end_date, is_end=True)
    stats = AuditLogService.get_stats(db=db, start_date=dt_start, end_date=dt_end)
    return {"data": stats}


@router.get("/export")
def export_logs(
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """
    Generates and downloads formal audit log reports in Excel (.xlsx) or PDF (.pdf) format.
    Supports time period filtering and multi-criteria query.
    """
    dt_start = _parse_datetime(start_date, is_end=False)
    dt_end = _parse_datetime(end_date, is_end=True)

    # Fetch all matching logs up to 1000 items for export
    items, total = AuditLogService.query_logs(
        db=db,
        page=1,
        page_size=1000,
        category=category,
        severity=severity,
        event_type=event_type,
        search=search,
        start_date=dt_start,
        end_date=dt_end,
    )

    stats = AuditLogService.get_stats(db=db, start_date=dt_start, end_date=dt_end)

    # Period label formatting
    if start_date and end_date:
        period_label = f"{start_date} to {end_date}"
    elif start_date:
        period_label = f"Since {start_date}"
    elif end_date:
        period_label = f"Until {end_date}"
    else:
        period_label = "All Log History"

    timestamp_str = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")

    if format.lower() == "pdf":
        pdf_bytes = AuditExportService.export_pdf(
            logs=items,
            stats=stats,
            period_label=period_label,
        )
        filename = f"NetBackup_Audit_Log_{timestamp_str}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        xlsx_bytes = AuditExportService.export_excel(
            logs=items,
            stats=stats,
            period_label=period_label,
        )
        filename = f"NetBackup_Audit_Log_{timestamp_str}.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@router.get("/{log_id}", response_model=dict[str, Any])
def get_log_detail(
    log_id: int,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """
    Returns full details of a specific audit log entry including raw JSON payload.
    """
    log_entry = db.get(SystemAuditLog, log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail="Audit log entry not found.")

    return {"data": AuditLogRead.model_validate(log_entry).model_dump(mode="json")}
