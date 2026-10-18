from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.database import get_db
from app.dependencies import AuthContext, get_current_context
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def parse_datetime(dt_str: str | None, is_end: bool = False) -> datetime:
    """
    Parse a user-supplied datetime/date string in ISO or common human formats,
    interpreting naive values in Asia/Jakarta timezone.
    """
    tz = ZoneInfo(settings.app_timezone)

    if not dt_str:
        now_local = datetime.now(tz)
        if is_end:
            return now_local.astimezone(timezone.utc)
        else:
            return (now_local - timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).astimezone(timezone.utc)

    clean_str = dt_str.strip()
    try:
        # Check if date-only format YYYY-MM-DD
        if len(clean_str) == 10 and clean_str.count("-") == 2:
            base_dt = datetime.strptime(clean_str, "%Y-%m-%d")
            if is_end:
                localized = base_dt.replace(hour=23, minute=59, second=59, tzinfo=tz)
            else:
                localized = base_dt.replace(hour=0, minute=0, second=0, tzinfo=tz)
            return localized.astimezone(timezone.utc)

        # Standard fromisoformat
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        raise AppError(
            status_code=422,
            code="INVALID_DATETIME_FORMAT",
            message=f"Invalid datetime format: '{clean_str}'. Expected ISO 8601 or YYYY-MM-DD.",
            details={"value": clean_str, "error": str(exc)},
        )


@router.get("/export")
def export_report(
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    start_date: str | None = Query(None, description="Start date (ISO or YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (ISO or YYYY-MM-DD)"),
    device_id: int | None = Query(None, description="Optional device ID filter"),
    status: str | None = Query(None, description="Optional status filter: all, success, failed"),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    """
    Export centralized backup execution audit records in Excel (.xlsx) or PDF format
    filtered by date range, device, and status.
    """
    start_dt = parse_datetime(start_date, is_end=False)
    end_dt = parse_datetime(end_date, is_end=True)

    if start_dt > end_dt:
        raise AppError(
            status_code=400,
            code="INVALID_DATE_RANGE",
            message="Start date cannot be after end date.",
        )

    service = ReportService(db)

    if format == "xlsx":
        excel_bytes, filename = service.generate_excel(
            start_dt=start_dt,
            end_dt=end_dt,
            device_id=device_id,
            status=status,
            user_name=ctx.user.username,
        )
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
    else:  # pdf
        pdf_bytes, filename = service.generate_pdf(
            start_dt=start_dt,
            end_dt=end_dt,
            device_id=device_id,
            status=status,
            user_name=ctx.user.username,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
