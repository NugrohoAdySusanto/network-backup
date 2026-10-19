from __future__ import annotations

from datetime import datetime, timezone
import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import Response

from app.database import Base
from app.models.audit_log import SystemAuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.audit_log_service import AuditLogService
from app.services.audit_export_service import AuditExportService
from app.core.security_middleware import security_audit_middleware


@pytest.fixture
def sqlite_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SystemAuditLog.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    yield session
    session.close()


def test_audit_log_create_and_query(sqlite_db_session: Session):
    # 1. Create multiple logs
    log1 = AuditLogService.create_log(
        db=sqlite_db_session,
        category="SECURITY",
        severity="CRITICAL",
        event_type="SQLI_ATTEMPT",
        message="SQL injection blocked on /api/v1/devices",
        source_ip="192.168.1.50",
        endpoint="GET /api/v1/devices",
        details={"payload": "' OR 1=1"},
    )
    log2 = AuditLogService.create_log(
        db=sqlite_db_session,
        category="AUDIT",
        severity="INFO",
        event_type="LOGIN_SUCCESS",
        message="User admin logged in successfully",
        username="admin",
        source_ip="192.168.1.10",
        endpoint="POST /api/v1/auth/login",
    )
    log3 = AuditLogService.create_log(
        db=sqlite_db_session,
        category="BACKUP_JOB",
        severity="ERROR",
        event_type="BACKUP_FAILED",
        message="Device core-sw-01 unreachable via SSH",
        source_ip="10.0.0.1",
        endpoint="CeleryWorker",
    )
    sqlite_db_session.commit()

    assert log1.id is not None
    assert log2.id is not None

    # Query all
    items, total = AuditLogService.query_logs(db=sqlite_db_session)
    assert total == 3
    assert len(items) == 3

    # Query by category
    sec_items, sec_total = AuditLogService.query_logs(db=sqlite_db_session, category="SECURITY")
    assert sec_total == 1
    assert sec_items[0].event_type == "SQLI_ATTEMPT"

    # Query by severity
    crit_items, crit_total = AuditLogService.query_logs(db=sqlite_db_session, severity="CRITICAL")
    assert crit_total == 1
    assert crit_items[0].severity == "CRITICAL"

    # Query by search keyword
    search_items, search_total = AuditLogService.query_logs(db=sqlite_db_session, search="core-sw-01")
    assert search_total == 1
    assert search_items[0].event_type == "BACKUP_FAILED"

    # Query by Log ID (Option 1)
    id_items, id_total = AuditLogService.query_logs(db=sqlite_db_session, search=f"LOG-{log1.id:06d}")
    assert id_total == 1
    assert id_items[0].id == log1.id

    # Query by #ID
    hash_items, hash_total = AuditLogService.query_logs(db=sqlite_db_session, search=f"#{log2.id}")
    assert hash_total == 1
    assert hash_items[0].id == log2.id

    # Schema computed fields test (Option 1 & 3)
    read_schema = AuditLogRead.model_validate(log1)
    assert read_schema.log_id == f"LOG-{log1.id:06d}"
    assert read_schema.request_id is None

    log_with_req = AuditLogService.create_log(
        db=sqlite_db_session,
        category="SECURITY",
        severity="WARNING",
        event_type="SUSPICIOUS_PATH",
        message="Attempt to access /etc/passwd",
        details={"request_id": "req_deadbeef1234"},
    )
    sqlite_db_session.commit()
    read_with_req = AuditLogRead.model_validate(log_with_req)
    assert read_with_req.log_id == f"LOG-{log_with_req.id:06d}"
    assert read_with_req.request_id == "req_deadbeef1234"

    # Query by request_id (Option 3)
    req_items, req_total = AuditLogService.query_logs(db=sqlite_db_session, search="deadbeef1234")
    assert req_total == 1
    assert req_items[0].id == log_with_req.id


def test_audit_log_stats_calculation(sqlite_db_session: Session):
    AuditLogService.create_log(
        db=sqlite_db_session,
        category="SECURITY",
        severity="CRITICAL",
        event_type="SQLI_ATTEMPT",
        message="Test SQLi",
    )
    AuditLogService.create_log(
        db=sqlite_db_session,
        category="SECURITY",
        severity="WARNING",
        event_type="LOGIN_FAILED",
        message="Failed login attempt",
    )
    AuditLogService.create_log(
        db=sqlite_db_session,
        category="BACKUP_JOB",
        severity="ERROR",
        event_type="JOB_FAILED",
        message="Job failed",
    )
    AuditLogService.create_log(
        db=sqlite_db_session,
        category="AUDIT",
        severity="INFO",
        event_type="LOGIN_SUCCESS",
        message="Login success",
    )
    sqlite_db_session.commit()

    stats = AuditLogService.get_stats(db=sqlite_db_session)
    assert stats["total_logs"] == 4
    assert stats["security_incidents"] == 2
    assert stats["failed_logins"] == 1
    assert stats["system_errors"] == 1
    assert stats["category_breakdown"]["SECURITY"] == 2
    assert stats["severity_breakdown"]["CRITICAL"] == 1


def test_audit_export_service_excel():
    log_sample = SystemAuditLog(
        id=1,
        created_at=datetime.now(timezone.utc),
        category="SECURITY",
        severity="CRITICAL",
        event_type="SQLI_ATTEMPT",
        source_ip="192.168.1.100",
        username="intruder",
        endpoint="GET /api/v1/devices",
        message="SQL injection blocked by security inspection.",
        details={"match": "union select"},
    )
    stats = {
        "total_logs": 1,
        "security_incidents": 1,
        "failed_logins": 0,
        "system_errors": 0,
        "category_breakdown": {"SECURITY": 1},
    }

    excel_bytes = AuditExportService.export_excel([log_sample], stats, "Test Period")
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000  # Valid Excel file size
    assert excel_bytes.startswith(b"PK")  # ZIP / XLSX magic header


def test_audit_export_service_pdf():
    log_sample = SystemAuditLog(
        id=1,
        created_at=datetime.now(timezone.utc),
        category="SECURITY",
        severity="CRITICAL",
        event_type="SQLI_ATTEMPT",
        source_ip="192.168.1.100",
        username="intruder",
        endpoint="GET /api/v1/devices",
        message="SQL injection blocked by security inspection.",
        details={"match": "union select"},
    )
    stats = {
        "total_logs": 1,
        "security_incidents": 1,
        "failed_logins": 0,
        "system_errors": 0,
    }

    pdf_bytes = AuditExportService.export_pdf([log_sample], stats, "Test Period")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")  # PDF magic marker


@pytest.mark.asyncio
async def test_security_middleware_blocks_sqli():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/devices",
        "query_string": b"search=' UNION SELECT 1,2,3--",
        "headers": [(b"host", b"localhost"), (b"user-agent", b"pytest-client")],
    }
    request = Request(scope)

    async def dummy_call_next(req):
        return Response(content="ok", status_code=200)

    response = await security_audit_middleware(request, dummy_call_next)
    assert response.status_code == 400
    assert b"MALICIOUS_PAYLOAD_DETECTED" in response.body


@pytest.mark.asyncio
async def test_security_middleware_blocks_xss():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/devices",
        "query_string": b"search=<script>alert(1)</script>",
        "headers": [(b"host", b"localhost"), (b"user-agent", b"pytest-client")],
    }
    request = Request(scope)

    async def dummy_call_next(req):
        return Response(content="ok", status_code=200)

    response = await security_audit_middleware(request, dummy_call_next)
    assert response.status_code == 400
    assert b"MALICIOUS_PAYLOAD_DETECTED" in response.body


@pytest.mark.asyncio
async def test_security_middleware_blocks_path_traversal():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/devices",
        "query_string": b"search=../../../../etc/passwd",
        "headers": [(b"host", b"localhost"), (b"user-agent", b"pytest-client")],
    }
    request = Request(scope)

    async def dummy_call_next(req):
        return Response(content="ok", status_code=200)

    response = await security_audit_middleware(request, dummy_call_next)
    assert response.status_code == 403
    assert b"MALICIOUS_PAYLOAD_DETECTED" in response.body


@pytest.mark.asyncio
async def test_security_middleware_passes_benign_request():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/devices",
        "query_string": b"search=router-jakarta-01&limit=20",
        "headers": [(b"host", b"localhost"), (b"user-agent", b"Mozilla/5.0")],
    }
    request = Request(scope)

    async def dummy_call_next(req):
        return Response(content="clean", status_code=200)

    response = await security_audit_middleware(request, dummy_call_next)
    assert response.status_code == 200
    assert response.body == b"clean"
