from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from app.services.report_service import ReportService
from app.api.reports import parse_datetime as api_parse_datetime


def test_parse_datetime_relative() -> None:
    # Test end default
    dt_end = api_parse_datetime(None, is_end=True)
    assert dt_end.tzinfo == timezone.utc

    # Test start default
    dt_start = api_parse_datetime(None, is_end=False)
    assert dt_start.tzinfo == timezone.utc
    assert dt_start < dt_end


def test_parse_datetime_date_only() -> None:
    dt = api_parse_datetime("2026-10-01", is_end=False)
    assert dt.tzinfo == timezone.utc
    # 2026-10-01 00:00:00 WIB is 2026-09-30 17:00:00 UTC
    assert dt.year == 2026 and dt.month == 9 and dt.day == 30 and dt.hour == 17

    dt_end = api_parse_datetime("2026-10-01", is_end=True)
    assert dt_end.tzinfo == timezone.utc
    # 2026-10-01 23:59:59 WIB is 2026-10-01 16:59:59 UTC
    assert dt_end.year == 2026 and dt_end.month == 10 and dt_end.day == 1 and dt_end.hour == 16


def test_parse_datetime_invalid() -> None:
    from app.core.errors import AppError
    with pytest.raises(AppError) as exc_info:
        api_parse_datetime("invalid-date-string")
    assert exc_info.value.code == "INVALID_DATETIME_FORMAT"


def test_generate_excel_and_pdf_mocked() -> None:
    from unittest.mock import MagicMock
    import openpyxl

    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 25

    # Create dummy jobs
    now = datetime.now(timezone.utc)

    mock_device = MagicMock()
    mock_device.hostname = "MKK-HQ_Router"
    mock_device.ip_address = "10.11.0.2"
    mock_device.vendor = "MikroTik"
    mock_device.model = "CCR1016-12G"

    mock_job1 = MagicMock()
    mock_job1.id = 1
    mock_job1.created_at = now
    mock_job1.device = mock_device
    mock_job1.driver_key = "mikrotik_routeros"
    mock_job1.trigger_type = "scheduled"
    mock_job1.state = "SUCCESS_NO_CHANGE"
    mock_job1.change_status = "no_change"
    mock_job1.zabbix_status_at_start = "available"
    mock_job1.raw_size_bytes = 45568
    mock_job1.normalized_size_bytes = 45568
    mock_job1.content_sha256 = "5b231550ea0123456789abcdef"
    mock_job1.snapshot = MagicMock()
    mock_job1.snapshot.config_object = MagicMock()
    mock_job1.snapshot.config_object.object_sha256 = "5b231550ea0123456789abcdef"
    mock_job1.duration_ms = 8000
    mock_job1.failure_stage = None
    mock_job1.failure_code = None
    mock_job1.failure_message = None

    mock_job2 = MagicMock()
    mock_job2.id = 2
    mock_job2.created_at = now - timedelta(hours=1)
    mock_job2.device = mock_device
    mock_job2.driver_key = "mikrotik_routeros"
    mock_job2.trigger_type = "manual"
    mock_job2.state = "FAILED"
    mock_job2.change_status = None
    mock_job2.zabbix_status_at_start = "available"
    mock_job2.raw_size_bytes = 0
    mock_job2.normalized_size_bytes = 0
    mock_job2.content_sha256 = None
    mock_job2.snapshot = None
    mock_job2.duration_ms = 12000
    mock_job2.failure_stage = "transport"
    mock_job2.failure_code = "CONNECTION_REFUSED"
    mock_job2.failure_message = "SSH connection refused by host"

    service = ReportService(mock_db)
    service.query_jobs = MagicMock(return_value=[mock_job1, mock_job2])

    start_dt = now - timedelta(days=7)
    end_dt = now

    # 1. Test Excel Generation
    xlsx_bytes, xlsx_filename = service.generate_excel(
        start_dt=start_dt,
        end_dt=end_dt,
        user_name="TestAdmin",
    )
    assert xlsx_filename.endswith(".xlsx")
    assert len(xlsx_bytes) > 0

    # Parse Excel workbook from bytes
    import io
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws.title == "Audit Execution Log"
    assert ws["A1"].value == "PT LUCKY MOM INDONESIA : NETWORK OPERATIONS CENTER"
    assert ws["B5"].value == "MONITORED DEVICES"
    assert ws["B6"].value == "25"
    assert ws["A8"].value == "No"
    # Row 9 is mock_job1
    assert ws.cell(row=9, column=3).value == "MKK-HQ_Router"
    assert ws.cell(row=9, column=9).value == "SUCCESS_NO_CHANGE"
    # Row 10 is mock_job2 (Failed)
    assert ws.cell(row=10, column=9).value == "FAILED"
    assert ws.cell(row=10, column=19).value == "SSH connection refused by host"

    # 2. Test PDF Generation
    pdf_bytes, pdf_filename = service.generate_pdf(
        start_dt=start_dt,
        end_dt=end_dt,
        user_name="TestAdmin",
    )
    assert pdf_filename.endswith(".pdf")
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # 3. Test CSV Generation
    csv_str, csv_filename = service.generate_csv(
        start_dt=start_dt,
        end_dt=end_dt,
    )
    assert csv_filename.endswith(".csv")
    assert "MKK-HQ_Router" in csv_str
