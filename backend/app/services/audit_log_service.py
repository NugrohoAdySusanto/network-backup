from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db_context
from app.models.audit_log import SystemAuditLog

logger = logging.getLogger(__name__)


class AuditLogService:
    """
    Centralized service for recording, querying, and analyzing system audit and security logs.
    """

    @staticmethod
    def create_log(
        db: Session,
        category: str,
        severity: str,
        event_type: str,
        message: str,
        source_ip: str | None = None,
        user_agent: str | None = None,
        user_id: int | None = None,
        username: str | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SystemAuditLog:
        """
        Records a new audit log entry within the provided database session.
        """
        # Standardize category: if None or empty, default to "UNKNOWN"
        clean_cat = (category or "").strip().upper()
        if not clean_cat:
            clean_cat = "UNKNOWN"

        clean_sev = (severity or "").strip().upper()
        if not clean_sev:
            clean_sev = "INFO"

        clean_evt = (event_type or "").strip().upper()
        if not clean_evt:
            clean_evt = "GENERAL_LOG"

        log_entry = SystemAuditLog(
            category=clean_cat,
            severity=clean_sev,
            event_type=clean_evt,
            message=message or "(No message recorded)",
            source_ip=source_ip,
            user_agent=user_agent[:255] if user_agent else None,
            user_id=user_id,
            username=username,
            endpoint=endpoint[:255] if endpoint else None,
            details=details or {},
        )
        db.add(log_entry)
        db.flush()
        return log_entry

    @classmethod
    def record_event_standalone(
        cls,
        category: str,
        severity: str,
        event_type: str,
        message: str,
        source_ip: str | None = None,
        user_agent: str | None = None,
        user_id: int | None = None,
        username: str | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Helper method to record an event using a standalone database session.
        Safely catches exceptions so audit logging failures never break primary execution.
        """
        try:
            with get_db_context() as db:
                cls.create_log(
                    db=db,
                    category=category,
                    severity=severity,
                    event_type=event_type,
                    message=message,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    user_id=user_id,
                    username=username,
                    endpoint=endpoint,
                    details=details,
                )
        except Exception as exc:
            logger.error("Failed to record standalone audit log event: %s", exc, exc_info=True)

    @staticmethod
    def query_logs(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        category: str | None = None,
        severity: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[SystemAuditLog], int]:
        """
        Queries paginated audit logs with dynamic multi-criteria filtering.
        Returns a tuple of (items, total_count).
        """
        query = select(SystemAuditLog)

        if category:
            query = query.where(SystemAuditLog.category == category.upper())
        if severity:
            query = query.where(SystemAuditLog.severity == severity.upper())
        if event_type:
            query = query.where(SystemAuditLog.event_type == event_type.upper())
        if start_date:
            query = query.where(SystemAuditLog.created_at >= start_date)
        if end_date:
            query = query.where(SystemAuditLog.created_at <= end_date)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    SystemAuditLog.message.ilike(search_pattern),
                    SystemAuditLog.source_ip.ilike(search_pattern),
                    SystemAuditLog.username.ilike(search_pattern),
                    SystemAuditLog.endpoint.ilike(search_pattern),
                    SystemAuditLog.event_type.ilike(search_pattern),
                )
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = db.scalar(count_stmt) or 0

        # Pagination & sorting
        offset = (max(page, 1) - 1) * page_size
        stmt = query.order_by(desc(SystemAuditLog.created_at)).offset(offset).limit(page_size)
        items = list(db.scalars(stmt).all())

        return items, total_count

    @staticmethod
    def get_stats(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Calculates aggregate statistics and KPI metrics for dashboard display.
        """
        conditions = []
        if start_date:
            conditions.append(SystemAuditLog.created_at >= start_date)
        if end_date:
            conditions.append(SystemAuditLog.created_at <= end_date)

        # Total logs in period
        total_stmt = select(func.count(SystemAuditLog.id))
        if conditions:
            total_stmt = total_stmt.where(*conditions)
        total_logs = db.scalar(total_stmt) or 0

        # Security threats count (CRITICAL or category SECURITY)
        sec_conds = list(conditions)
        sec_conds.append(
            or_(
                SystemAuditLog.category == "SECURITY",
                SystemAuditLog.severity == "CRITICAL",
            )
        )
        security_incidents = db.scalar(select(func.count(SystemAuditLog.id)).where(*sec_conds)) or 0

        # Failed logins count
        login_conds = list(conditions)
        login_conds.append(SystemAuditLog.event_type == "LOGIN_FAILED")
        failed_logins = db.scalar(select(func.count(SystemAuditLog.id)).where(*login_conds)) or 0

        # Errors count
        err_conds = list(conditions)
        err_conds.append(SystemAuditLog.severity == "ERROR")
        system_errors = db.scalar(select(func.count(SystemAuditLog.id)).where(*err_conds)) or 0

        # Category Breakdown
        cat_stmt = select(SystemAuditLog.category, func.count(SystemAuditLog.id))
        if conditions:
            cat_stmt = cat_stmt.where(*conditions)
        cat_stmt = cat_stmt.group_by(SystemAuditLog.category)
        category_breakdown = {cat: count for cat, count in db.execute(cat_stmt).all()}

        # Severity Breakdown
        sev_stmt = select(SystemAuditLog.severity, func.count(SystemAuditLog.id))
        if conditions:
            sev_stmt = sev_stmt.where(*conditions)
        sev_stmt = sev_stmt.group_by(SystemAuditLog.severity)
        severity_breakdown = {sev: count for sev, count in db.execute(sev_stmt).all()}

        return {
            "total_logs": total_logs,
            "security_incidents": security_incidents,
            "failed_logins": failed_logins,
            "system_errors": system_errors,
            "category_breakdown": category_breakdown,
            "severity_breakdown": severity_breakdown,
        }
