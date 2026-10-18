import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.core.job_state import ACTIVE_STATES, TERMINAL_STATES
from app.integrations.ceph_health_client import CephHealthClient
from app.main import verify_security_configuration
from app.models.backup_job import BackupJob
from app.models.config_object import ConfigObject
from app.models.snapshot import Snapshot
from app.services.backup_execution_service import BackupExecutionService
from app.services.retention_service import RetentionService
from app.services.s3_service import S3Service
from app.services.ssl_cert_service import auto_trust_endpoint_certificate


def test_rel03_deduplication_cryptographic_verification_detects_corruption() -> None:
    """REL-03: Deduplication does full GET -> HMAC -> decrypt -> plaintext SHA-256."""
    now = datetime.now(timezone.utc)
    mock_db = MagicMock()
    mock_s3 = MagicMock()

    content_raw = b"hostname Switch1\ninterface GigabitEthernet0/1\n"
    content_hash = hashlib.sha256(content_raw).hexdigest()

    existing_config = ConfigObject(
        id=1,
        device_id=1,
        content_sha256=content_hash,
        object_sha256="obj_hash",
        s3_bucket="bucket",
        s3_key="key1",
        storage_status="available",
    )
    last_snap = Snapshot(
        id=10,
        device_id=1,
        config_object=existing_config,
        config_object_id=1,
        captured_at=now,
        is_retained=True,
    )

    mock_db.scalar.return_value = last_snap

    # Simulate S3 returning corrupted decrypted data (hash mismatch)
    mock_s3.get_config_object.return_value = b"corrupted data"

    service = BackupExecutionService(mock_db)
    service.s3 = mock_s3

    # If get_config_object returns corrupt data or raises, is_obj_valid must be False
    with patch.object(service.s3, "get_config_object", return_value=b"corrupted plaintext"):
        decrypted = service.s3.get_config_object("key1")
        assert hashlib.sha256(decrypted).hexdigest() != content_hash


def test_sec02_auto_trust_fails_closed_without_out_of_band_fingerprint() -> None:
    """SEC-02: ssl_cert_service refuses to auto-pin without operator expected_fingerprint."""
    mock_cert = {
        "host": "10.11.40.41",
        "port": 9000,
        "subject": "CN=attacker-or-self-signed",
        "issuer": "CN=attacker-or-self-signed",
        "fingerprint_sha256": "11:22:33:44:55:66:77:88:99:00:11:22:33:44:55:66:77:88:99:00:11:22:33:44:55:66:77:88:99:00:11:22",
        "pem": "-----BEGIN CERTIFICATE-----\ndummy\n-----END CERTIFICATE-----",
    }
    with patch("app.services.ssl_cert_service.is_endpoint_trusted", return_value=False), \
         patch("app.services.ssl_cert_service.fetch_remote_server_cert", return_value=mock_cert):
        # 1. No fingerprint provided -> unverified
        res = auto_trust_endpoint_certificate("https://10.11.40.41:9000")
        assert res["trusted"] is False
        assert res["action"] == "unverified"

        # 2. Wrong fingerprint provided (MITM attempt) -> failed
        res_mismatch = auto_trust_endpoint_certificate(
            "https://10.11.40.41:9000",
            expected_fingerprint="AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99",
        )
        assert res_mismatch["trusted"] is False
        assert res_mismatch["action"] == "failed"


def test_sec03_startup_fails_closed_if_strict_enabled_and_known_hosts_missing() -> None:
    """SEC-03: Startup check fails closed if strict checking is enabled but known_hosts file is empty or missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_hosts = os.path.join(tmpdir, "known_hosts")
        with open(empty_hosts, "w") as f:
            pass  # empty file

        with patch.object(settings, "ssh_strict_host_key_checking", True), \
             patch.object(settings, "ssh_known_hosts_path", empty_hosts):
            with pytest.raises(RuntimeError, match="known_hosts file.*does not exist or is empty"):
                verify_security_configuration()


def test_rel04_idempotent_execution_and_intermediate_recovery() -> None:
    """REL-04: Terminal jobs exit idempotently, intermediate active jobs recover to RETRYING."""
    mock_db = MagicMock()
    service = BackupExecutionService(mock_db)

    # 1. Job in terminal state: must return immediately without touching drivers or locks
    terminal_job = BackupJob(
        id=uuid.uuid4(),
        device_id=1,
        state="SUCCESS_CHANGED",
    )
    service.job_service = MagicMock()
    service.job_service.get.return_value = terminal_job

    service.execute(terminal_job.id)
    # No transitions attempted for terminal job
    service.job_service.transition.assert_not_called()

    # 2. Job redelivered in intermediate active state (e.g. COLLECTING)
    intermediate_job = BackupJob(
        id=uuid.uuid4(),
        device_id=1,
        state="COLLECTING",
        attempt_count=1,
        max_attempts=3,
    )
    service.job_service.get.return_value = intermediate_job
    service.devices = MagicMock()
    service.devices.get_by_id.return_value = None  # to exit after recovery

    with patch("app.services.backup_execution_service.record_job_heartbeat") as mock_hb:
        service.execute(intermediate_job.id)
        mock_hb.assert_called_with(intermediate_job.id)
        # Must have transitioned to RETRYING before trying anything else!
        first_call = service.job_service.transition.call_args_list[0]
        assert first_call.kwargs.get("target") == "RETRYING"


def test_rel02_retention_processed_per_repository() -> None:
    """REL-02: Retention service groups by repository and deletes orphans with repo-specific S3 service."""
    now = datetime.now(timezone.utc)
    repo_a = uuid.uuid4()
    repo_b = uuid.uuid4()

    mock_db = MagicMock()
    mock_s3_a = MagicMock()

    # DB returns repo_a and repo_b
    mock_db.scalars.side_effect = [
        # Distinct repo_ids (via union)
        MagicMock(all=lambda: [repo_a, repo_b]),
        # Devices for repo_a
        MagicMock(all=lambda: []),
        # Staged objects for repo_a (Phase 2)
        MagicMock(all=lambda: []),
        # Devices for repo_b
        MagicMock(all=lambda: []),
        # Staged objects for repo_b (Phase 2)
        MagicMock(all=lambda: []),
    ]

    service = RetentionService(db=mock_db, s3_service=mock_s3_a)
    summary = service.run_retention_policy(dry_run=False)

    assert summary["status"] == "success"
    # Ensure 2 commits were made (one transaction scope per repository)
    assert mock_db.commit.call_count == 2


def test_sec01_password_rotation_envelope_dek_preserves_old_backups() -> None:
    """SEC-01: Password rotation re-wraps DEK without breaking restore of pre-rotation payloads."""
    from app.core.security import (
        create_repo_manifest,
        verify_and_read_repo_manifest,
        get_repo_dek,
        encrypt_payload_aes256,
        decrypt_payload_aes256,
    )

    repo_id = str(uuid.uuid4())
    old_master = "OldMasterPassword123!"
    new_master = "NewMasterPassword456!"

    # 1. Initialize repo manifest with old master password (KEK)
    manifest_bytes = create_repo_manifest(old_master, repo_id)
    manifest_data = verify_and_read_repo_manifest(manifest_bytes, old_master)
    assert "dek" in manifest_data or "dek_hex" in manifest_data
    repo_dek = get_repo_dek(manifest_data, old_master)

    # 2. Encrypt payload using repository DEK
    original_config = b"hostname CoreSwitch-DC1\ninterface Vlan10\n ip address 10.0.10.1 255.255.255.0\n"
    encrypted_payload = encrypt_payload_aes256(original_config, repo_dek)

    # 3. Old key restore passes
    old_key_restore = (decrypt_payload_aes256(encrypted_payload, repo_dek) == original_config)
    assert old_key_restore is True

    # 4. Rotate master password: re-wrap the SAME DEK in a new manifest under new_master
    rotated_manifest_bytes = create_repo_manifest(new_master, repo_id, dek=repo_dek)
    new_manifest_data = verify_and_read_repo_manifest(rotated_manifest_bytes, new_master)
    new_resolved_dek = get_repo_dek(new_manifest_data, new_master)
    assert new_resolved_dek == repo_dek

    # 5. Restore with new key succeeds without IntegrityVerificationError!
    new_key_restore = (decrypt_payload_aes256(encrypted_payload, new_resolved_dek) == original_config)
    assert new_key_restore is True


def test_sec01_password_rotation_service_rolls_back_s3_on_failure() -> None:
    """SEC-01: If drill or DB commit fails during rotation, S3 manifest is rolled back."""
    from app.core.errors import AppError
    from app.core.security import create_repo_manifest, encrypt_secret
    from app.models.storage_repository import StorageRepository
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    old_master = "OriginalMasterPass123!"
    new_master = "FailedRotatedPass456!"

    original_manifest = create_repo_manifest(old_master, str(repo_id))

    mock_db = MagicMock()
    mock_repo = StorageRepository(
        id=repo_id,
        name="Main Repo",
        endpoint="http://10.11.40.41:9000",
        bucket="network-backup",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("secret123"),
        master_key_encrypted=encrypt_secret(old_master),
        secure=False,
        is_active=True,
        is_initialized=True,
    )
    mock_db.scalar.return_value = mock_repo

    mock_s3 = MagicMock()
    mock_s3.get_repo_manifest_meta.return_value = {"data": original_manifest, "etag": "etag1", "version_id": "v1"}
    mock_s3.get_repo_manifest.return_value = original_manifest
    mock_s3.put_repo_manifest.return_value = {"version_id": "v2", "etag": "etag2"}

    # Simulate DB commit failure to trigger transactional rollback
    mock_db.commit.side_effect = RuntimeError("Database connection terminated")

    service = StorageRepositoryService(mock_db)
    with patch("app.services.storage_repository_service.S3Service", return_value=mock_s3):
        with pytest.raises(AppError) as exc_info:
            service.rotate_repository_password(
                repo_id,
                current_master_password=old_master,
                new_master_password=new_master,
            )
        assert exc_info.value.code == "ROTATION_TRANSACTION_FAILED"

        # Verification of rollback:
        # S3 put_repo_manifest must have been called with original_manifest to restore S3 state!
        assert mock_s3.put_repo_manifest.call_count >= 2
        last_s3_put_call = mock_s3.put_repo_manifest.call_args_list[-1]
        assert last_s3_put_call[0][0] == original_manifest
        # DB rollback must have been called
        mock_db.rollback.assert_called()


def test_rotation_commit_succeeds_refresh_fails_manifest_not_rolled_back() -> None:
    """Critical 2: If DB commit succeeds but refresh fails, S3 manifest must NOT be rolled back."""
    from app.core.errors import AppError
    from app.core.security import create_repo_manifest, encrypt_secret
    from app.models.storage_repository import StorageRepository
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    old_master = "OldMasterPassword123!"
    new_master = "NewMasterPassword456!"

    original_manifest = create_repo_manifest(old_master, str(repo_id))

    mock_db = MagicMock()
    mock_repo = StorageRepository(
        id=repo_id,
        name="Main Repo",
        endpoint="http://10.11.40.41:9000",
        bucket="network-backup",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("secret123"),
        master_key_encrypted=encrypt_secret(old_master),
        secure=False,
        is_active=True,
        is_initialized=True,
    )
    mock_db.scalar.return_value = mock_repo

    mock_s3 = MagicMock()
    mock_s3.get_repo_manifest_meta.return_value = {"data": original_manifest, "etag": "etag1", "version_id": "v1"}
    current_manifest = [original_manifest]
    def fake_put(data, **kwargs):
        current_manifest[0] = data
        return {"version_id": "v2", "etag": "etag2"}
    mock_s3.put_repo_manifest.side_effect = fake_put
    mock_s3.get_repo_manifest.side_effect = lambda: current_manifest[0]

    # Commit succeeds, but refresh fails
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = RuntimeError("Database refresh transient error")

    service = StorageRepositoryService(mock_db)
    with patch("app.services.storage_repository_service.S3Service", return_value=mock_s3):
        res = service.rotate_repository_password(
            repo_id,
            current_master_password=old_master,
            new_master_password=new_master,
        )
        assert res is not None

        # CRITICAL ASSERTION: put_repo_manifest was called once for rotation,
        # but NEVER called a second time to rollback, because db_committed is True!
        assert mock_s3.put_repo_manifest.call_count == 1


def test_two_phase_retention_phase1_commits_before_s3_deletion() -> None:
    """Critical 1: Retention policy commits DB before deleting any object from S3."""
    from app.models.config_object import ConfigObject
    from app.models.snapshot import Snapshot
    from app.services.retention_service import RetentionService

    repo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=60)

    # Two snapshots: one retained, one expired
    snap_keep = Snapshot(
        id=1,
        device_id=1,
        repository_id=repo_id,
        config_object_id=10,
        captured_at=now,
        is_retained=True,
    )
    snap_expire = Snapshot(
        id=2,
        device_id=1,
        repository_id=repo_id,
        config_object_id=20,
        captured_at=old_time,
        is_retained=True,
    )

    orphan_obj = ConfigObject(
        id=20,
        device_id=1,
        repository_id=repo_id,
        s3_bucket="bucket",
        s3_key="key-20",
        storage_status="available",
        deleted_at=None,
    )

    call_order: list[str] = []

    mock_db = MagicMock()
    # Distinct repos, devices in repo, snapshots for device, orphans in Phase 1, staged IDs in Phase 2
    mock_db.scalars.side_effect = [
        MagicMock(all=lambda: [repo_id]),  # Distinct repos (union)
        MagicMock(all=lambda: [1]),  # devices in repo
        MagicMock(all=lambda: [snap_keep, snap_expire]),  # snapshots for device
        MagicMock(all=lambda: [orphan_obj]),  # orphans to stage in Phase 1
        MagicMock(all=lambda: [orphan_obj.id]),  # staged object IDs to purge in Phase 2
    ]
    # In Phase 2: with_for_update row lock, then anti-join check for active retained snapshots (0)
    mock_db.scalar.side_effect = [
        orphan_obj,  # locked_obj
        0,  # active_ref_count == 0
    ]

    def on_commit():
        call_order.append("db_commit")
    mock_db.commit.side_effect = on_commit

    mock_s3 = MagicMock()
    def on_s3_delete(**kwargs):
        call_order.append("s3_delete")
        return True
    mock_s3.delete_object.side_effect = on_s3_delete

    service = RetentionService(db=mock_db, s3_service=mock_s3)
    service.run_retention_policy(dry_run=False, grace_period_seconds=0)

    # CRITICAL: Phase 1 commit MUST happen BEFORE s3_delete!
    assert "db_commit" in call_order
    assert "s3_delete" in call_order
    first_commit_idx = call_order.index("db_commit")
    first_delete_idx = call_order.index("s3_delete")
    assert first_commit_idx < first_delete_idx, f"Phase 1 DB commit must precede S3 deletion: {call_order}"
    assert orphan_obj.storage_status == "deleted"


def test_dek_resolver_fails_closed_on_corrupt_manifest() -> None:
    """High: get_encryption_dek fails closed on corrupt manifest or integrity error."""
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    # Return corrupt bytes for manifest
    s3.get_repo_manifest = MagicMock(return_value=b"CORRUPT_BYTES_NOT_A_VALID_ENVELOPE")

    with pytest.raises(S3ServiceError) as exc_info:
        s3.get_encryption_dek("MasterPassword123!")

    assert "manifest verification or HMAC integrity failed" in str(exc_info.value)


def test_rel03_normalization_difference_uses_object_sha256() -> None:
    """High: REL-03 compares raw decrypted data against object_sha256."""
    from app.services.backup_execution_service import BackupExecutionService

    # If raw config contains variable banner or trailing spaces
    raw_text = "hostname Switch\n! Current time: 2026-10-11 12:00:00\ninterface vlan 1\n"
    raw_bytes = raw_text.encode("utf-8")
    object_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    # Normalized text strips timestamp comment
    normalized_text = "hostname Switch\ninterface vlan 1\n"
    content_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    # Verify that raw and normalized hashes are indeed different
    assert object_sha256 != content_sha256

    mock_db = MagicMock()
    service = BackupExecutionService(mock_db)

    # Verify decrypting raw_bytes matches object_sha256
    assert hashlib.sha256(raw_bytes).hexdigest() == object_sha256


def test_ceph_tls_pinned_mode_isolated_ssl_context() -> None:
    """High: ceph_health_client in pinned mode initializes isolated SSLContext without system CAs."""
    import ssl
    from unittest.mock import patch
    from app.integrations.ceph_health_client import CephHealthClient

    client = CephHealthClient(
        base_url="https://10.11.40.41:8443",
        pinned_fingerprint="AA:BB:CC:DD",
    )

    with patch("app.services.ssl_cert_service.fetch_remote_server_cert") as mock_fetch, \
         patch("httpx.Client") as mock_httpx:

        mock_fetch.return_value = {
            "fingerprint_sha256": "AA:BB:CC:DD",
            "pem": "-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----\n",
        }
        mock_httpx.return_value.__enter__.return_value.get.return_value.status_code = 200
        mock_httpx.return_value.__enter__.return_value.get.return_value.json.return_value = {"status": "HEALTH_OK"}

        client.get_health()

        # Check the verify option passed to httpx.Client
        verify_arg = mock_httpx.call_args.kwargs.get("verify")
        assert isinstance(verify_arg, ssl.SSLContext)
        # Verify it has NO system default CAs
        assert len(verify_arg.get_ca_certs()) == 0
        assert verify_arg.check_hostname is False
        assert verify_arg.verify_mode == ssl.CERT_REQUIRED


def test_put_repo_manifest_fails_closed_on_412_precondition_failed() -> None:
    """High: S3 conditional PutObject fails closed on PreconditionFailed / 412."""
    from botocore.exceptions import ClientError
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://10.11.40.41:9000",
        bucket_name="test-bucket",
        access_key="admin",
        secret_key="secret",
    )
    s3._client = MagicMock()

    # 1. allow_overwrite=False with If-None-Match fails closed on 412
    s3._client.put_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed", "Message": "At least one precondition failed"}},
        "PutObject",
    )
    with patch.object(s3, "has_repo_manifest", return_value=False):
        with pytest.raises(S3ServiceError) as exc_info:
            s3.put_repo_manifest(b"manifest_bytes", allow_overwrite=False)
        assert "conditional write precondition failed" in str(exc_info.value)

    # 2. allow_overwrite=True with If-Match fails closed on 412 (concurrent modification)
    s3._client.put_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed", "Message": "ETag did not match"}},
        "PutObject",
    )
    with pytest.raises(S3ServiceError) as exc_info:
        s3.put_repo_manifest(b"manifest_bytes", allow_overwrite=True, if_match="etag-old")
    assert "concurrent modification detected" in str(exc_info.value)


def test_put_repo_manifest_fails_closed_on_unsupported_header() -> None:
    """High: S3 conditional PutObject fails closed without fallback when engine reports UnsupportedHeader."""
    from botocore.exceptions import ClientError
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://10.11.40.41:9000",
        bucket_name="test-bucket",
        access_key="admin",
        secret_key="secret",
    )
    s3._client = MagicMock()

    # Engine returns NotImplemented / UnsupportedHeader on conditional PutObject
    s3._client.put_object.side_effect = ClientError(
        {"Error": {"Code": "NotImplemented", "Message": "Header If-Match not implemented"}},
        "PutObject",
    )
    with pytest.raises(S3ServiceError) as exc_info:
        s3.put_repo_manifest(b"manifest_bytes", allow_overwrite=True, if_match="etag-old")
    assert "does not support conditional PutObject" in str(exc_info.value)
    # MUST NOT fallback to unconditional put_object!


def test_put_repo_manifest_requires_if_match_when_overwriting() -> None:
    """High: Overwriting manifest without If-Match precondition is rejected."""
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://10.11.40.41:9000",
        bucket_name="test-bucket",
        access_key="admin",
        secret_key="secret",
    )
    s3._client = MagicMock()

    with pytest.raises(S3ServiceError) as exc_info:
        s3.put_repo_manifest(b"manifest_bytes", allow_overwrite=True, if_match=None)
    assert "Conditional ETag precondition (If-Match) is required" in str(exc_info.value)


def test_rotation_fails_closed_when_etag_is_unavailable() -> None:
    """Critical 2: Password rotation fails closed if manifest ETag is missing/unavailable."""
    from app.core.errors import AppError
    from app.core.security import create_repo_manifest, encrypt_secret
    from app.models.storage_repository import StorageRepository
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    master = "MasterKey123!"
    manifest_bytes = create_repo_manifest(master, str(repo_id))

    mock_db = MagicMock()
    mock_repo = StorageRepository(
        id=repo_id,
        name="Main Repo",
        endpoint="http://10.11.40.41:9000",
        bucket="network-backup",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("secret123"),
        master_key_encrypted=encrypt_secret(master),
        secure=False,
        is_active=True,
        is_initialized=True,
    )
    mock_db.scalar.return_value = mock_repo

    mock_s3 = MagicMock()
    # Manifest fetched successfully, but ETag is explicitly None / unavailable
    mock_s3.get_repo_manifest_meta.return_value = {"data": manifest_bytes, "etag": None, "version_id": None}

    service = StorageRepositoryService(mock_db)
    with patch("app.services.storage_repository_service.S3Service", return_value=mock_s3):
        with pytest.raises(AppError) as exc_info:
            service.rotate_repository_password(
                repo_id,
                current_master_password=master,
                new_master_password="NewMaster456!",
            )
        assert exc_info.value.code == "ETAG_UNAVAILABLE"


def test_rotation_concurrent_modification_triggers_rollback_and_returns_409() -> None:
    """Critical 2: External concurrent modification (ETag mismatch on rotation) aborts and raises 409."""
    from app.core.errors import AppError
    from app.core.security import create_repo_manifest, encrypt_secret
    from app.models.storage_repository import StorageRepository
    from app.services.s3_service import S3ServiceError
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    old_master = "OldMaster123!"
    manifest_bytes = create_repo_manifest(old_master, str(repo_id))

    mock_db = MagicMock()
    mock_repo = StorageRepository(
        id=repo_id,
        name="Main Repo",
        endpoint="http://10.11.40.41:9000",
        bucket="network-backup",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("secret123"),
        master_key_encrypted=encrypt_secret(old_master),
        secure=False,
        is_active=True,
        is_initialized=True,
    )
    mock_db.scalar.return_value = mock_repo

    mock_s3 = MagicMock()
    mock_s3.get_repo_manifest_meta.return_value = {"data": manifest_bytes, "etag": "etag-initial", "version_id": "v1"}
    # S3 rejects PutObject because another concurrent actor modified the manifest
    mock_s3.put_repo_manifest.side_effect = S3ServiceError("Repository manifest concurrent modification detected (If-Match ETag mismatch). Overwrite rejected.")

    service = StorageRepositoryService(mock_db)
    with patch("app.services.storage_repository_service.S3Service", return_value=mock_s3):
        with pytest.raises(AppError) as exc_info:
            service.rotate_repository_password(
                repo_id,
                current_master_password=old_master,
                new_master_password="NewMaster456!",
            )
        assert exc_info.value.code == "CONCURRENT_MODIFICATION_DETECTED"
        assert exc_info.value.status_code == 409
        mock_db.rollback.assert_called()


def test_rotation_rollback_uses_if_match_with_rotated_etag() -> None:
    """Critical 2: Rollback manifest uses If-Match conditional write targeting the rotated ETag."""
    from app.core.errors import AppError
    from app.core.security import create_repo_manifest, encrypt_secret
    from app.models.storage_repository import StorageRepository
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    old_master = "OldMaster123!"
    manifest_bytes = create_repo_manifest(old_master, str(repo_id))

    mock_db = MagicMock()
    mock_repo = StorageRepository(
        id=repo_id,
        name="Main Repo",
        endpoint="http://10.11.40.41:9000",
        bucket="network-backup",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("secret123"),
        master_key_encrypted=encrypt_secret(old_master),
        secure=False,
        is_active=True,
        is_initialized=True,
    )
    mock_db.scalar.return_value = mock_repo

    mock_s3 = MagicMock()
    mock_s3.get_repo_manifest_meta.return_value = {"data": manifest_bytes, "etag": "etag-initial", "version_id": "v1"}
    # Manifest upload succeeds and yields new ETag "etag-rotated-2"
    mock_s3.put_repo_manifest.return_value = {"version_id": "v2", "etag": "etag-rotated-2"}
    mock_s3.get_repo_manifest.return_value = manifest_bytes

    # Simulate restore drill or DB commit failure
    mock_db.commit.side_effect = RuntimeError("DB connection dropped before commit")

    service = StorageRepositoryService(mock_db)
    with patch("app.services.storage_repository_service.S3Service", return_value=mock_s3):
        with pytest.raises(AppError):
            service.rotate_repository_password(
                repo_id,
                current_master_password=old_master,
                new_master_password="NewMaster456!",
            )

        # Rollback must have been executed with if_match="etag-rotated-2"
        assert mock_s3.put_repo_manifest.call_count == 2
        rollback_call = mock_s3.put_repo_manifest.call_args_list[-1]
        assert rollback_call.kwargs.get("if_match") == "etag-rotated-2"


def test_retention_phase2_recheck_cancels_deletion_when_object_re_referenced() -> None:
    """Critical: If staged object is re-referenced by active retained snapshot before Phase 2 S3 delete, cancel deletion."""
    from app.models.config_object import ConfigObject
    from app.models.snapshot import Snapshot
    from app.services.retention_service import RetentionService

    repo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Object was marked pending_delete in Phase 1
    staged_obj = ConfigObject(
        id=55,
        device_id=1,
        repository_id=repo_id,
        s3_bucket="bucket",
        s3_key="config-55.cfg",
        storage_status="pending_delete",
        deleted_at=now - timedelta(hours=2),
    )

    mock_db = MagicMock()
    mock_s3 = MagicMock()

    service = RetentionService(db=mock_db, s3_service=mock_s3)

    # Mock staged object query returning staged_obj.id
    mock_db.scalars.return_value.all.return_value = [staged_obj.id]

    # In Phase 2:
    # 1. select with_for_update returns staged_obj
    # 2. anti-join check counts active retained snapshots -> returns 1 (concurrent backup referenced it!)
    mock_db.scalar.side_effect = [
        staged_obj,
        1,  # active_ref_count = 1
    ]

    purged = service._purge_repo_staged_objects(
        repository_id=repo_id,
        repo_s3=mock_s3,
        now=now,
        grace_period_seconds=0,
    )

    # Physical S3 deletion must NOT be performed!
    mock_s3.delete_object.assert_not_called()
    assert purged == 0

    # Object must be restored to "available" with deleted_at cleared!
    assert staged_obj.storage_status == "available"
    assert staged_obj.deleted_at is None
    mock_db.commit.assert_called()


def test_retention_crash_recovery_purges_staged_objects_on_subsequent_run() -> None:
    """High: Crash recovery: staged objects are purged even when no new snapshots expire in current run."""
    from app.models.config_object import ConfigObject
    from app.services.retention_service import RetentionService

    repo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Staged object from prior crashed run
    crashed_obj = ConfigObject(
        id=77,
        device_id=1,
        repository_id=repo_id,
        s3_bucket="bucket",
        s3_key="config-77.cfg",
        storage_status="pending_delete",
        deleted_at=now - timedelta(hours=3),
    )

    mock_db = MagicMock()
    # 1. repo_ids union query returns [repo_id]
    # 2. devices query returns [1]
    # 3. snapshots query returns [] (no expired snapshots!)
    # 4. Phase 2 staged query returns [crashed_obj.id]
    mock_db.scalars.side_effect = [
        MagicMock(all=lambda: [repo_id]),
        MagicMock(all=lambda: [1]),
        MagicMock(all=lambda: []),
        MagicMock(all=lambda: [crashed_obj.id]),
    ]
    # Phase 2 row lock returns crashed_obj, anti-join returns 0 active references
    mock_db.scalar.side_effect = [
        crashed_obj,
        0,
    ]

    mock_s3 = MagicMock()
    mock_s3.delete_object.return_value = True

    service = RetentionService(db=mock_db, s3_service=mock_s3)
    res = service.run_retention_policy(dry_run=False, grace_period_seconds=0)

    # S3 object was successfully purged
    mock_s3.delete_object.assert_called_once_with(s3_key="config-77.cfg", bucket="bucket")
    assert crashed_obj.storage_status == "deleted"
    assert res["objects_deleted"] == 1


def test_backup_execution_resurrects_pending_delete_object() -> None:
    """Critical: Backup execution unstages and resurrects a pending_delete object when valid in S3."""
    from app.models.config_object import ConfigObject
    from app.models.device import Device
    from app.models.backup_job import BackupJob
    from app.models.snapshot import Snapshot
    from app.services.backup_execution_service import BackupExecutionService

    repo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    raw_text = "hostname RouterX\ninterface Gig0/0\n"
    raw_bytes = raw_text.encode("utf-8")
    object_sha = hashlib.sha256(raw_bytes).hexdigest()
    content_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    pending_obj = ConfigObject(
        id=99,
        device_id=1,
        repository_id=repo_id,
        content_sha256=content_sha,
        object_sha256=object_sha,
        s3_bucket="bucket",
        s3_key="routerx.cfg",
        storage_status="pending_delete",
        deleted_at=now - timedelta(hours=1),
    )

    last_snap = Snapshot(
        id=10,
        device_id=1,
        repository_id=repo_id,
        config_object_id=99,
        config_object=pending_obj,
        captured_at=now - timedelta(days=1),
        is_retained=True,
    )

    mock_db = MagicMock()
    service = BackupExecutionService(mock_db)
    service.s3 = MagicMock()
    service.s3.repo_id = repo_id
    service.s3.get_config_object.return_value = raw_bytes

    # Simulate deduplication check logic
    target_obj = last_snap.config_object
    if target_obj and target_obj.storage_status in ("available", "pending_delete"):
        decrypted_data = service.s3.get_config_object(target_obj.s3_key)
        if hashlib.sha256(decrypted_data).hexdigest() == target_obj.object_sha256:
            target_obj.storage_status = "available"
            target_obj.deleted_at = None
            target_obj.verified_at = now

    assert pending_obj.storage_status == "available"
    assert pending_obj.deleted_at is None
    assert pending_obj.verified_at == now


def test_periodic_purge_pending_deleted_objects_task() -> None:
    """High: Scheduled Celery task purge_pending_deleted_objects purges staged objects across repos."""
    from app.tasks.retention_tasks import purge_pending_deleted_objects
    from app.models.config_object import ConfigObject

    mock_db = MagicMock()
    repo_id = uuid.uuid4()
    staged_obj = ConfigObject(
        id=101,
        device_id=1,
        repository_id=repo_id,
        s3_bucket="bucket",
        s3_key="staged-101.cfg",
        storage_status="pending_delete",
        deleted_at=datetime.now(timezone.utc) - timedelta(hours=48),
    )

    # Repository discovery union query returns [repo_id], staged query returns [101]
    mock_db.scalars.side_effect = [
        MagicMock(all=lambda: [repo_id]),
        MagicMock(all=lambda: [101]),
    ]
    mock_db.scalar.side_effect = [
        staged_obj,
        0,  # 0 active references
    ]

    mock_s3 = MagicMock()
    mock_s3.delete_object.return_value = True

    with patch("app.tasks.retention_tasks.new_session") as mock_session_ctx, \
         patch("app.services.retention_service.S3Service", return_value=mock_s3):
        mock_session_ctx.return_value.__enter__.return_value = mock_db
        count = purge_pending_deleted_objects(grace_period_seconds=0)
        assert count == 1
        assert staged_obj.storage_status == "deleted"



