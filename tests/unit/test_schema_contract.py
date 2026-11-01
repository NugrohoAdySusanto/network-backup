from app.core.enums import BackupJobState, RetentionMarkType, RetentionPolicy
from app.database import Base
import app.models  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "devices",
    "device_backup_settings",
    "backup_jobs",
    "config_objects",
    "snapshots",
    "snapshot_retention_marks",
    "integration_status",
    "custom_drivers",
    "storage_repositories",
    "system_audit_logs",
    "repository_device_setting_archives",
}


def test_expected_tables_registered() -> None:
    assert EXPECTED_TABLES == set(Base.metadata.tables)


def test_backup_job_terminal_states_exist() -> None:
    assert BackupJobState.SUCCESS_CHANGED.value == "SUCCESS_CHANGED"
    assert BackupJobState.SUCCESS_NO_CHANGE.value == "SUCCESS_NO_CHANGE"
    assert BackupJobState.SKIPPED_DEVICE_DOWN.value == "SKIPPED_DEVICE_DOWN"
    assert BackupJobState.SKIPPED_STATUS_UNKNOWN.value == "SKIPPED_STATUS_UNKNOWN"
    assert BackupJobState.FAILED.value == "FAILED"


def test_retention_contract_values() -> None:
    assert RetentionPolicy.STANDARD_31.value == "standard_31"
    assert RetentionPolicy.SMART_7_4_12_3.value == "smart_7_4_12_3"
    assert RetentionMarkType.LATEST_GOOD.value == "LATEST_GOOD"


def test_serialize_device_last_backup_contract() -> None:
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from app.api.devices import _serialize_device

    device = MagicMock()
    device.id = 100
    device.zabbix_host_id = "10100"
    device.hostname = "TEST-DEVICE"
    device.ip_address = "192.168.1.1"
    device.vendor = "Ruijie"
    device.model = "S2910"
    device.host_group = "Switches"
    device.availability_status = "up"
    device.availability_checked_at = None
    device.zabbix_last_sync_at = None
    device.source_present = True
    device.backup_settings = None

    # Case 1: No jobs and no snapshots
    device.snapshots = []
    device.backup_jobs = []
    serialized = _serialize_device(device)
    assert serialized["last_backup"] is None

    # Case 2: Succeeded job
    now = datetime.now(timezone.utc)
    job_success = MagicMock()
    job_success.id = "00000000-0000-0000-0000-000000000001"
    job_success.state = "SUCCESS_NO_CHANGE"
    job_success.trigger_type = "scheduled"
    job_success.created_at = now
    job_success.finished_at = now
    job_success.change_status = "no_change"
    job_success.failure_message = None
    job_success.failure_code = None
    job_success.duration_ms = 1200
    device.backup_jobs = [job_success]

    snap = MagicMock()
    snap.id = 55
    snap.captured_at = now
    snap.change_status = "no_change"
    snap.display_filename = "test_config.txt"
    device.snapshots = [snap]

    serialized = _serialize_device(device)
    assert serialized["last_backup"]["status"] == "success"
    assert serialized["last_backup"]["state"] == "SUCCESS_NO_CHANGE"
    assert serialized["last_backup"]["trigger_type"] == "scheduled"
    assert serialized["last_backup"]["id"] == 55

    # Case 3: Failed job (more recent than job_success)
    from datetime import timedelta
    job_fail = MagicMock()
    job_fail.id = "00000000-0000-0000-0000-000000000002"
    job_fail.state = "FAILED"
    job_fail.trigger_type = "manual"
    job_fail.created_at = now + timedelta(minutes=10)
    job_fail.finished_at = now + timedelta(minutes=11)
    job_fail.change_status = None
    job_fail.failure_message = "SSH Connection Timeout"
    job_fail.failure_code = "SSH_TIMEOUT"
    job_fail.duration_ms = 15000
    device.backup_jobs = [job_success, job_fail]

    serialized = _serialize_device(device)
    assert serialized["last_backup"]["status"] == "failed"
    assert serialized["last_backup"]["state"] == "FAILED"
    assert serialized["last_backup"]["failure_message"] == "SSH Connection Timeout"


def test_verify_schema_contract_detects_missing_tables():
    import pytest
    from unittest.mock import MagicMock, patch
    from app.main import verify_schema_contract

    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["users", "devices"]  # missing others

    with patch("app.main.inspect", return_value=mock_inspector):
        with pytest.raises(RuntimeError) as exc_info:
            verify_schema_contract()
        assert "Missing required tables" in str(exc_info.value)


def test_verify_schema_contract_detects_missing_columns():
    import pytest
    from unittest.mock import MagicMock, patch
    from app.main import verify_schema_contract, EXPECTED_TABLES

    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = list(EXPECTED_TABLES)
    mock_inspector.get_columns.side_effect = lambda table: []  # no columns

    with patch("app.main.inspect", return_value=mock_inspector):
        with pytest.raises(RuntimeError) as exc_info:
            verify_schema_contract()
        assert "Column 'storage_repositories.master_key_encrypted' is missing" in str(exc_info.value)


