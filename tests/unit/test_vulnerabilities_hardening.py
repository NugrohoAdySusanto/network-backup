import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import paramiko
import pytest
from sqlalchemy import Index

from app.config import settings
from app.drivers.base import DeviceConnectionContext
from app.drivers.netmiko_base import BaseNetmikoDriver
from app.drivers.ruijie_switch import RuijieSwitchDriver
from app.integrations.ceph_health_client import CephHealthClient
from app.models.config_object import ConfigObject
from app.models.snapshot import Snapshot
from app.models.storage_repository import StorageRepository
from app.services.retention_service import RetentionService


def test_ceph_health_client_verifies_tls() -> None:
    """SEC-02: Verify Ceph client enables TLS validation with hostname verification or pinned fingerprint."""
    import certifi
    with patch("app.services.ssl_cert_service.ensure_ca_bundle") as mock_ca:
        mock_ca.return_value = certifi.where()
        with patch("httpx.Client") as mock_httpx:
            mock_client_inst = MagicMock()
            mock_httpx.return_value.__enter__.return_value = mock_client_inst
            mock_client_inst.get.return_value.is_success = True
            mock_client_inst.get.return_value.json.return_value = {"health": {"status": "HEALTH_OK"}}

            # Case 1: No pinned fingerprint -> strictly enforce check_hostname = True
            client = CephHealthClient(base_url="https://ceph.example.com", token="dummy", pinned_fingerprint="")
            client.get_health()

            _, kwargs = mock_httpx.call_args
            verify_val = kwargs.get("verify")
            assert verify_val is not False
            if hasattr(verify_val, "verify_mode"):
                import ssl
                assert verify_val.verify_mode == ssl.CERT_REQUIRED
                assert verify_val.check_hostname is True

            # Case 2: Pinned fingerprint -> verifies peer cert and uses pinned SSL context
            dummy_fp = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99"
            mock_cert = {
                "fingerprint_sha256": dummy_fp,
                "pem": "-----BEGIN CERTIFICATE-----\ndummy\n-----END CERTIFICATE-----",
            }
            with patch("app.services.ssl_cert_service.fetch_remote_server_cert", return_value=mock_cert):
                client_pinned = CephHealthClient(
                    base_url="https://ceph.example.com",
                    token="dummy",
                    pinned_fingerprint=dummy_fp,
                )
                res = client_pinned.get_health()
                assert res.status == "HEALTH_OK"




def test_ssh_drivers_strict_host_key_checking() -> None:
    """SEC-03: Verify Netmiko drivers use strict host key enforcement."""
    driver = RuijieSwitchDriver()
    ctx = DeviceConnectionContext(
        device_id=1,
        hostname="router1",
        host="10.0.0.1",
        port=22,
        username="admin",
        password="secret",
        enable_password="enable_pass",
        connect_timeout=15,
        command_timeout=30,
    )
    params = driver.get_connection_parameters(ctx)
    assert params["ssh_strict"] == settings.ssh_strict_host_key_checking
    assert params["system_host_keys"] is True



def test_ruijie_driver_restores_paramiko_transport_preferences() -> None:
    """SEC-03: Verify Ruijie driver restores global paramiko settings in finally block."""
    initial_keys = tuple(paramiko.Transport._preferred_keys)
    initial_kex = tuple(paramiko.Transport._preferred_kex)

    driver = RuijieSwitchDriver()
    ctx = DeviceConnectionContext(
        device_id=2,
        hostname="switch1",
        host="10.0.0.2",
        port=22,
        username="admin",
        password="secret",
        connect_timeout=15,
        command_timeout=30,
    )

    with patch.object(BaseNetmikoDriver, "connect") as mock_connect:
        mock_connect.side_effect = RuntimeError("Simulated connection error")
        with pytest.raises(RuntimeError):
            driver.connect(ctx)

    # After execution (even after error), global paramiko settings MUST be restored
    assert tuple(paramiko.Transport._preferred_keys) == initial_keys
    assert tuple(paramiko.Transport._preferred_kex) == initial_kex


def test_multi_repo_unique_constraints_defined() -> None:
    """ARCH-01: Verify multi-repo unique constraints in model metadata."""
    # Check ConfigObject indexes include repository_id
    config_indexes = {
        idx.name: [col.name if hasattr(col, "name") else str(col) for col in idx.columns]
        for idx in ConfigObject.__table__.indexes
    }
    assert "uq_config_object_content" in config_indexes
    assert "repository_id" in config_indexes["uq_config_object_content"]
    assert "content_sha256" in config_indexes["uq_config_object_content"]

    assert "uq_config_object_s3_key" in config_indexes
    assert "repository_id" in config_indexes["uq_config_object_s3_key"]
    assert "s3_key" in config_indexes["uq_config_object_s3_key"]

    # Check StorageRepository partial unique index for single active repository
    repo_indexes = {idx.name: idx for idx in StorageRepository.__table__.indexes}
    assert "uq_storage_repositories_single_active" in repo_indexes
    active_idx = repo_indexes["uq_storage_repositories_single_active"]
    assert active_idx.unique is True


def test_retention_service_latest_known_good_guard() -> None:
    """REL-02: Verify Latest Known Good snapshot is NEVER expired even if older than 31 days."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=60)
    repo_id = uuid.uuid4()

    # Only one snapshot for device 10, but 60 days old
    old_snapshot = Snapshot(
        id=101,
        device_id=10,
        repository_id=repo_id,
        backup_job_id=uuid.uuid4(),
        config_object_id=1,
        captured_at=old_time,
        change_status="baseline",
        retention_policy_at_capture="standard_31",
        display_filename="old_backup.cfg",
        is_retained=True,
    )

    mock_db = MagicMock()
    mock_db.scalars.side_effect = [
        # First query: distinct repository_ids
        MagicMock(all=lambda: [repo_id]),
        # Second query: distinct device_ids in repo
        MagicMock(all=lambda: [10]),
        # Third query: snapshots for device 10 in repo
        MagicMock(all=lambda: [old_snapshot]),
        # Fourth query: Phase 2 purge staged ConfigObjects for repo
        MagicMock(all=lambda: []),
    ]

    service = RetentionService(db=mock_db, s3_service=MagicMock())
    summary = service.run_retention_policy(dry_run=False)

    assert summary["status"] == "success"
    assert summary["snapshots_retained"] == 1
    assert summary["snapshots_expired"] == 0
    # Guard kept old_snapshot active!
    assert old_snapshot.is_retained is True

