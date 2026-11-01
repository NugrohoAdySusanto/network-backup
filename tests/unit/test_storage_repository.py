import pytest
import uuid
from unittest.mock import MagicMock, patch
from app.core.security import (
    create_repo_manifest,
    verify_and_read_repo_manifest,
    encrypt_secret,
    decrypt_secret,
)
from app.models.storage_repository import StorageRepository


def test_secret_encryption_and_decryption_roundtrip():
    secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    # Length of base64 envelope for AES-256-CBC + HMAC-SHA256 (16B salt + 16B iv + 32B mac + ciphertext) >= 140
    assert len(encrypted) >= 120
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret


def test_database_credential_vault_legacy_fernet_fallback():
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from app.config import settings

    # Simulate a legacy credential encrypted under Fernet (AES-128)
    key_bytes = hashlib.sha256(settings.app_secret.encode("utf-8")).digest()
    fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
    legacy_ciphertext = fernet.encrypt(b"LegacySecretValue128").decode("utf-8")

    # decrypt_secret should seamlessly decrypt legacy tokens
    recovered = decrypt_secret(legacy_ciphertext)
    assert recovered == "LegacySecretValue128"


def test_repo_manifest_encryption_and_password_verification():
    from app.core.security_errors import RepositoryManifestVerificationError

    repo_id = str(uuid.uuid4())
    master_pass = "SuperSecretMasterKey123!"

    manifest_bytes = create_repo_manifest(
        master_password=master_pass,
        repo_id=repo_id,
    )
    assert isinstance(manifest_bytes, bytes)
    assert len(manifest_bytes) > 32

    # Verify with correct password
    verified = verify_and_read_repo_manifest(manifest_bytes, master_pass)
    assert verified is not None
    assert verified["repo_id"] == repo_id
    assert verified["magic"] == "NETWORK_BACKUP_REPO_V1"
    assert verified["cipher"] == "AES-256-CBC+HMAC-SHA256"

    # Verify that wrong password raises RepositoryManifestVerificationError fail-closed
    with pytest.raises(RepositoryManifestVerificationError):
        verify_and_read_repo_manifest(manifest_bytes, "IncorrectPassword!")


def test_storage_repository_model_instantiation():
    repo_id = uuid.uuid4()
    repo = StorageRepository(
        id=repo_id,
        name="Secondary Backup Pool",
        endpoint="https://s3.example.com",
        bucket="secondary-netbackup",
        access_key="ACCESSKEY123",
        secret_key_encrypted="ENCRYPTED_SECRET",
        secure=True,
        is_active=False,
        is_initialized=True,
    )
    assert str(repo.id) == str(repo_id)
    assert repo.name == "Secondary Backup Pool"
    assert repo.is_active is False
    assert repo.is_initialized is True


def test_test_connection_enforces_ssl_for_https():
    from unittest.mock import MagicMock
    from app.services.storage_repository_service import StorageRepositoryService

    mock_db = MagicMock()
    svc = StorageRepositoryService(mock_db)

    # Test with HTTPS and secure=False -> must fail with SSL validation requirement message
    res = svc.test_connection(
        endpoint="https://s3.example.com",
        bucket="test-bucket",
        access_key="ACCESS",
        secret_key="SECRET",
        secure=False,
    )
    assert res["success"] is False
    assert "SSL Certificate Validation is required for HTTPS endpoints" in res["message"]


def test_payload_encryption_and_decryption_aes256():
    from app.core.security import encrypt_payload_aes256, decrypt_payload_aes256
    from app.core.security_errors import IntegrityVerificationError

    config_data = b"hostname Core-Router-01\ninterface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n"
    master_pass = "MyMasterPassword2026!"

    encrypted = encrypt_payload_aes256(config_data, master_pass)
    assert encrypted != config_data
    assert len(encrypted) >= 80

    decrypted = decrypt_payload_aes256(encrypted, master_pass)
    assert decrypted == config_data

    # Wrong password raises IntegrityVerificationError fail-closed (no plaintext returned)
    with pytest.raises(IntegrityVerificationError):
        decrypt_payload_aes256(encrypted, "WrongPass123!")

    # Tampered ciphertext raises IntegrityVerificationError
    tampered = bytearray(encrypted)
    tampered[-2] ^= 0x01
    with pytest.raises(IntegrityVerificationError):
        decrypt_payload_aes256(bytes(tampered), master_pass)


def test_credential_vault_fail_closed_on_corrupt_data():
    from app.core.security_errors import CredentialDecryptionError, IntegrityVerificationError

    # Random corrupt string must raise CredentialDecryptionError, never return as-is
    with pytest.raises(CredentialDecryptionError):
        decrypt_secret("invalid-corrupt-base64-payload!!!")

    # Tampered valid vault token must raise IntegrityVerificationError or CredentialDecryptionError
    valid_token = encrypt_secret("SecretAccessKey123")
    import base64
    raw = bytearray(base64.urlsafe_b64decode(valid_token.encode("utf-8")))
    raw[-2] ^= 0x01  # tamper ciphertext
    tampered_b64 = base64.urlsafe_b64encode(raw).decode("utf-8")
    with pytest.raises(IntegrityVerificationError):
        decrypt_secret(tampered_b64)


def test_ruijie_driver_fails_closed_when_enable_password_missing():
    from app.drivers.base import DeviceConnectionContext, DriverConfigurationError
    from app.drivers.ruijie_switch import RuijieSwitchDriver

    driver = RuijieSwitchDriver()
    context = DeviceConnectionContext(
        device_id=1,
        hostname="Switch-Core",
        host="10.10.10.1",
        port=22,
        username="admin",
        password="password",
        connect_timeout=5,
        command_timeout=10,
        enable_password=None,  # Missing!
    )

    with pytest.raises(DriverConfigurationError) as exc_info:
        driver.get_connection_parameters(context)
    assert "NETWORK_SSH_ENABLE_PASSWORD is not configured" in str(exc_info.value)


def test_s3_upload_rejected_when_repo_missing():
    from unittest.mock import MagicMock, patch
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    s3._client = MagicMock()
    with patch.object(S3Service, "_get_repo_from_db", return_value=None):
        with pytest.raises(S3ServiceError) as exc_info:
            s3.put_config_object(s3_key="config.txt", data=b"show run")
        assert "Repository configuration cannot be resolved" in str(exc_info.value)
        s3._client.put_object.assert_not_called()


def test_s3_upload_rejected_when_master_key_missing():
    from unittest.mock import MagicMock, patch
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    s3._client = MagicMock()
    fake_repo = MagicMock()
    fake_repo.id = "fake-repo-1"
    fake_repo.master_key_encrypted = None

    with patch.object(S3Service, "_get_repo_from_db", return_value=fake_repo):
        with pytest.raises(S3ServiceError) as exc_info:
            s3.put_config_object(s3_key="config.txt", data=b"show run")
        assert "Repository master credential is missing" in str(exc_info.value)
        s3._client.put_object.assert_not_called()


def test_s3_upload_crypto_failure_prevents_put_object():
    from unittest.mock import MagicMock, patch
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    s3._client = MagicMock()
    fake_repo = MagicMock()
    fake_repo.id = "fake-repo-1"
    fake_repo.master_key_encrypted = "corrupt-invalid-token!!!"

    with patch.object(S3Service, "_get_repo_from_db", return_value=fake_repo):
        with pytest.raises(S3ServiceError) as exc_info:
            s3.put_config_object(s3_key="config.txt", data=b"show run")
        assert "Master credential decryption failed" in str(exc_info.value)
        # S3 put_object MUST NOT be called on crypto failure
        s3._client.put_object.assert_not_called()


def test_s3_download_rejected_when_master_key_missing():
    from unittest.mock import MagicMock, patch
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    s3._client = MagicMock()
    # Mock S3 get_object returning raw ciphertext
    raw_cipher = b"\x00" * 96
    mock_body = MagicMock()
    mock_body.read.return_value = raw_cipher
    s3._client.get_object.return_value = {"Body": mock_body}

    fake_repo = MagicMock()
    fake_repo.id = "fake-repo-1"
    fake_repo.master_key_encrypted = None

    with patch.object(S3Service, "_get_repo_from_db", return_value=fake_repo), \
         patch.object(S3Service, "_is_positively_identified_legacy", return_value=False):
        # Must fail-closed: never silently return raw/plain object
        with pytest.raises(S3ServiceError) as exc_info:
            s3.get_config_object("config.txt")
        assert "master credential is missing" in str(exc_info.value).lower()


def test_s3_valid_encrypted_object_decrypts_correctly():
    from unittest.mock import MagicMock, patch
    from app.core.security import encrypt_payload_aes256, encrypt_secret
    from app.services.s3_service import S3Service

    master_password = "MasterKeyTestSecretPass123!"
    master_key_encrypted = encrypt_secret(master_password)

    plain_config = b"hostname CoreRouter\ninterface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n"
    encrypted_blob = encrypt_payload_aes256(plain_config, master_password)

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    from app.core.security import create_repo_manifest
    s3._client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = encrypted_blob

    manifest_bytes = create_repo_manifest(master_password, "fake-repo-1")
    manifest_body = MagicMock()
    manifest_body.read.return_value = manifest_bytes

    def mock_get_object(*args, **kwargs):
        key = kwargs.get("Key")
        if key == "repo_manifest.enc":
            return {"Body": manifest_body}
        return {"Body": mock_body}

    s3._client.get_object.side_effect = mock_get_object

    fake_repo = MagicMock()
    fake_repo.id = "fake-repo-1"
    fake_repo.master_key_encrypted = master_key_encrypted

    with patch.object(S3Service, "_get_repo_from_db", return_value=fake_repo):
        result = s3.get_config_object("config.txt")
        assert result == plain_config


def test_put_repo_manifest_overwrite_prohibited():
    from unittest.mock import MagicMock, patch
    from app.services.s3_service import S3Service, S3ServiceError

    s3 = S3Service(
        endpoint_url="http://s3.example.com",
        bucket_name="test-bucket",
        access_key="test-key",
        secret_key="test-secret",
    )
    s3._client = MagicMock()

    with patch.object(s3, "has_repo_manifest", return_value=True):
        # Default allow_overwrite=False must raise S3ServiceError
        with pytest.raises(S3ServiceError) as exc_info:
            s3.put_repo_manifest(b"dummy_data", allow_overwrite=False)
        assert "Overwrite prohibited" in str(exc_info.value)
        s3._client.put_object.assert_not_called()

        # allow_overwrite=True requires if_match
        with pytest.raises(S3ServiceError) as exc_if_match:
            s3.put_repo_manifest(b"dummy_data", allow_overwrite=True)
        assert "Conditional ETag precondition" in str(exc_if_match.value)

        # allow_overwrite=True with if_match succeeds
        s3._client.put_object.return_value = {"VersionId": "v123", "ETag": '"etag123"'}
        res = s3.put_repo_manifest(b"dummy_data", allow_overwrite=True, if_match="etag123")
        assert res["version_id"] == "v123"
        assert res["etag"] == "etag123"


def test_initialize_repository_rejected_when_manifest_exists():
    from unittest.mock import MagicMock, patch
    from app.core.errors import AppError
    from app.services.storage_repository_service import StorageRepositoryService
    from app.services.s3_service import S3Service

    mock_db = MagicMock()
    svc = StorageRepositoryService(mock_db)

    with patch.object(S3Service, "has_repo_manifest", return_value=True):
        with pytest.raises(AppError) as exc_info:
            svc.initialize_repository(
                name="New Repo",
                endpoint="http://s3.example.com",
                bucket="test-bucket",
                access_key="ACCESS",
                secret_key="SECRET",
                secure=False,
                master_password="StrongMasterPass123!",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "REPOSITORY_ALREADY_INITIALIZED"


def test_initialize_repository_success_with_restore_drill():
    from unittest.mock import MagicMock, patch
    from app.core.security import create_repo_manifest
    from app.services.storage_repository_service import StorageRepositoryService
    from app.services.s3_service import S3Service

    mock_db = MagicMock()
    svc = StorageRepositoryService(mock_db)
    master_pass = "ValidStrongPass123!"

    with patch.object(S3Service, "has_repo_manifest", return_value=False), \
         patch.object(S3Service, "put_repo_manifest", return_value={"version_id": "v1", "etag": "etag1"}), \
         patch.object(S3Service, "get_repo_manifest") as mock_get:
        
        # Make get_repo_manifest return a valid manifest matching the repo_id
        def fake_get_manifest():
            # Generate a valid manifest under master_pass
            # repo_id will be captured from create_repo_manifest call or generated
            return create_repo_manifest(master_pass, str(mock_db.add.call_args[0][0].id) if mock_db.add.called else None)

        # To ensure the drill matches repo_id, patch create_repo_manifest
        orig_create = create_repo_manifest
        captured_manifests = []
        def mocked_create(pwd, rid=None):
            m = orig_create(pwd, rid)
            captured_manifests.append(m)
            return m

        with patch("app.services.storage_repository_service.create_repo_manifest", side_effect=mocked_create):
            mock_get.side_effect = lambda: captured_manifests[-1]
            repo = svc.initialize_repository(
                name="Fresh Repo",
                endpoint="http://s3.example.com",
                bucket="my-bucket",
                access_key="ACCESS",
                secret_key="SECRET",
                secure=False,
                master_password=master_pass,
            )
            assert repo.is_active is True
            assert repo.repo_manifest["restore_drill_passed"] is True
            assert repo.repo_manifest["version_id"] == "v1"
            assert repo.repo_manifest["etag"] == "etag1"
            mock_db.commit.assert_called_once()


def test_serialize_device_s3_disconnected_resets_settings_and_history():
    from unittest.mock import MagicMock
    from app.api.devices import _serialize_device

    device = MagicMock()
    device.id = 1
    device.zabbix_host_id = "1001"
    device.hostname = "DEVICE-01"
    device.ip_address = "10.0.0.1"
    device.vendor = "Ruijie"
    device.model = "AP"
    device.host_group = "WLAN"
    device.availability_status = "up"
    device.availability_checked_at = None
    device.zabbix_last_sync_at = None
    device.source_present = True

    setting = MagicMock()
    setting.driver_key = "ruijie-ap"
    setting.schedule_enabled = True
    setting.retention_policy = "smart_7_4_12_3"
    device.backup_settings = setting

    # Device has old snapshots and old repo jobs
    old_snap = MagicMock()
    old_snap.repository_id = "old-repo-uuid"
    device.snapshots = [old_snap]

    old_job = MagicMock()
    old_job.repository_id = "old-repo-uuid"
    old_job.state = "SUCCESS_NO_CHANGE"
    device.backup_jobs = [old_job]

    # When S3 is disconnected (is_s3_connected=False)
    res = _serialize_device(device, active_repo_id=None, is_s3_connected=False)
    assert res["backup_settings"]["driver_key"] is None
    assert res["backup_settings"]["schedule_enabled"] is False
    assert res["backup_settings"]["next_run_at"] is None
    assert res["last_backup"] is None


def test_serialize_device_s3_disconnected_clears_last_backup_and_alerts():
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from app.api.devices import _serialize_device

    device = MagicMock()
    device.id = 1
    device.zabbix_host_id = "1001"
    device.hostname = "DEVICE-01"
    device.ip_address = "10.0.0.1"
    device.vendor = "Ruijie"
    device.model = "AP"
    device.host_group = "WLAN"
    device.availability_status = "up"
    device.availability_checked_at = None
    device.zabbix_last_sync_at = None
    device.source_present = True
    device.backup_settings = None
    device.snapshots = []

    now = datetime.now(timezone.utc)
    disconnected_job = MagicMock()
    disconnected_job.id = "job-disc-1"
    disconnected_job.repository_id = None
    disconnected_job.state = "FAILED"
    disconnected_job.failure_code = "STORAGE_DISCONNECTED"
    disconnected_job.failure_message = "S3 storage is disconnected."
    disconnected_job.trigger_type = "manual"
    disconnected_job.created_at = now
    disconnected_job.finished_at = now
    disconnected_job.change_status = None
    disconnected_job.duration_ms = 0
    device.backup_jobs = [disconnected_job]

    res = _serialize_device(device, active_repo_id=None, is_s3_connected=False)
    assert res["last_backup"] is None


def test_serialize_device_scopes_to_active_repository():
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from app.api.devices import _serialize_device

    device = MagicMock()
    device.id = 1
    device.zabbix_host_id = "1001"
    device.hostname = "DEVICE-01"
    device.ip_address = "10.0.0.1"
    device.vendor = "Ruijie"
    device.model = "AP"
    device.host_group = "WLAN"
    device.availability_status = "up"
    device.availability_checked_at = None
    device.zabbix_last_sync_at = None
    device.source_present = True
    device.backup_settings = None

    now = datetime.now(timezone.utc)
    repo_a_job = MagicMock()
    repo_a_job.id = "job-a"
    repo_a_job.repository_id = "repo-a-uuid"
    repo_a_job.state = "SUCCESS_NO_CHANGE"
    repo_a_job.trigger_type = "manual"
    repo_a_job.created_at = now
    repo_a_job.finished_at = now
    repo_a_job.change_status = "no_change"
    repo_a_job.failure_code = None
    repo_a_job.failure_message = None
    repo_a_job.duration_ms = 100

    repo_a_snap = MagicMock()
    repo_a_snap.id = 101
    repo_a_snap.repository_id = "repo-a-uuid"
    repo_a_snap.captured_at = now
    repo_a_snap.change_status = "no_change"
    repo_a_snap.display_filename = "config.txt"

    device.backup_jobs = [repo_a_job]
    device.snapshots = [repo_a_snap]

    # When connected to repo A: repo A history is shown
    res_a = _serialize_device(device, active_repo_id="repo-a-uuid", is_s3_connected=True)
    assert res_a["last_backup"]["id"] == 101
    assert res_a["last_backup"]["status"] == "success"

    # When connected to a brand new repo B: repo A history is NOT shown
    res_b = _serialize_device(device, active_repo_id="repo-b-uuid", is_s3_connected=True)
    assert res_b["last_backup"] is None


def test_delete_repository():
    mock_db = MagicMock()
    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.name = "Test Repo"
    mock_repo.is_active = True

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_repo

    from app.services.storage_repository_service import StorageRepositoryService
    svc = StorageRepositoryService(mock_db)
    res = svc.delete_repository(repo_id)

    assert res["success"] is True
    assert res["was_active"] is True
    mock_db.delete.assert_called_once_with(mock_repo)
    mock_db.commit.assert_called()


def test_delete_repository_not_found():
    from app.core.errors import AppError
    from app.services.storage_repository_service import StorageRepositoryService
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    svc = StorageRepositoryService(mock_db)
    with pytest.raises(AppError) as exc_info:
        svc.delete_repository(uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_dashboard_summary_scoped_to_active_repo():
    from app.api.dashboard import get_dashboard_summary
    from app.models.storage_repository import StorageRepository

    mock_db = MagicMock()
    # Case: No active repository -> rate 0.0, successful 0
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.count.return_value = 5
    mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 5

    res = get_dashboard_summary(_=MagicMock(), db=mock_db)
    assert res["data"]["successful_devices_today"] == 0
    assert res["data"]["backup_success_rate_today"] == 0.0
    assert "zabbix" in res["data"]
    assert "is_synced" in res["data"]["zabbix"]
    assert "status" in res["data"]["zabbix"]


def test_password_rotation_re_wraps_dek_and_payload_remains_decryptable():
    """End-to-end test: S3 payload encrypted with DEK before rotation decrypts after master key rotation."""
    from app.core.security import encrypt_secret, create_repo_manifest
    from app.models.storage_repository import StorageRepository
    from app.services.s3_service import S3Service
    from app.services.storage_repository_service import StorageRepositoryService

    repo_id = uuid.uuid4()
    old_password = "MasterPasswordAlpha123!"
    new_password = "MasterPasswordBeta456!"

    # In-memory S3 bucket storage mock
    s3_storage: dict[str, bytes] = {}

    initial_manifest = create_repo_manifest(old_password, str(repo_id))
    s3_storage["repo_manifest.enc"] = initial_manifest

    mock_repo = StorageRepository(
        id=repo_id,
        name="Primary Repository",
        endpoint="http://10.11.40.41:9000",
        bucket="test-bucket",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("s3secret"),
        master_key_encrypted=encrypt_secret(old_password),
        secure=False,
        is_active=True,
        is_initialized=True,
    )

    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_repo
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_repo

    # Mock S3 client simulating S3 put/get object against s3_storage dict
    def fake_put_object(**kwargs):
        s3_storage[kwargs["Key"]] = kwargs["Body"]
        return {"ETag": '"dummy-etag"', "VersionId": "v1"}

    def fake_get_object(**kwargs):
        key = kwargs["Key"]
        if key not in s3_storage:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        body_mock = MagicMock()
        body_mock.read.return_value = s3_storage[key]
        return {"Body": body_mock, "ETag": '"dummy-etag"'}

    mock_boto = MagicMock()
    mock_boto.put_object.side_effect = fake_put_object
    mock_boto.get_object.side_effect = fake_get_object

    with patch("boto3.client", return_value=mock_boto), \
         patch("app.services.s3_service.S3Service._get_repo_from_db", return_value=mock_repo):
        # 1. Initialize S3 service before rotation and store encrypted backup
        s3_pre = S3Service(repo_id=repo_id)
        s3_pre._client = mock_boto
        test_payload = b"version 15.2\nhostname Router1\nline vty 0 4\n login\n"
        s3_pre.put_config_object(s3_key="configs/router1.cfg", data=test_payload)

        # 2. Verify payload decrypts before rotation
        restored_pre = s3_pre.get_config_object("configs/router1.cfg")
        assert restored_pre == test_payload

        # 3. Perform Master Password Rotation via StorageRepositoryService
        repo_svc = StorageRepositoryService(mock_db)
        repo_svc.rotate_repository_password(
            repo_id,
            current_master_password=old_password,
            new_master_password=new_password,
        )

        # Verify DB record was updated to new password
        mock_db.commit.assert_called()

        # 4. Now instantiate S3 service with rotated repository state (new master password)
        s3_post = S3Service(repo_id=repo_id)
        s3_post._client = mock_boto
        restored_post = s3_post.get_config_object("configs/router1.cfg")

        # 5. Restoring OLD backup with NEW master password MUST SUCCEED (envelope DEK preserved)!
        assert restored_post == test_payload


def test_password_rotation_legacy_repo_migration_preserves_restore():
    """Rotating a legacy repository without envelope DEK preserves restore capability for existing backups."""
    from app.core.security import encrypt_secret, _derive_keys_aes256_hmac
    from app.models.storage_repository import StorageRepository
    from app.services.s3_service import S3Service
    from app.services.storage_repository_service import StorageRepositoryService
    import hashlib, hmac, json, os
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    repo_id = uuid.uuid4()
    old_password = "LegacyMasterKey123!"
    new_password = "NewRotatedKey456!"

    # Create a legacy manifest WITHOUT dek or dek_hex
    salt = os.urandom(16)
    iv = os.urandom(16)
    enc_key, mac_key = _derive_keys_aes256_hmac(old_password, salt)
    legacy_payload = {
        "magic": "NETWORK_BACKUP_REPO_V1",
        "cipher": "AES-256-CBC+HMAC-SHA256",
        "repo_id": str(repo_id),
        "status": "active",
    }
    plaintext = json.dumps(legacy_payload).encode("utf-8")
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
    mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()
    legacy_manifest_bytes = salt + iv + mac + ciphertext

    s3_storage: dict[str, bytes] = {
        "repo_manifest.enc": legacy_manifest_bytes,
    }

    mock_repo = StorageRepository(
        id=repo_id,
        name="Legacy Repository",
        endpoint="http://10.11.40.41:9000",
        bucket="legacy-bucket",
        access_key="admin",
        secret_key_encrypted=encrypt_secret("s3secret"),
        master_key_encrypted=encrypt_secret(old_password),
        secure=False,
        is_active=True,
        is_initialized=True,
    )

    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_repo
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_repo

    def fake_put_object(**kwargs):
        s3_storage[kwargs["Key"]] = kwargs["Body"]
        return {"ETag": '"etag"', "VersionId": "v1"}

    def fake_get_object(**kwargs):
        body_mock = MagicMock()
        body_mock.read.return_value = s3_storage[kwargs["Key"]]
        return {"Body": body_mock, "ETag": '"etag"'}

    mock_boto = MagicMock()
    mock_boto.put_object.side_effect = fake_put_object
    mock_boto.get_object.side_effect = fake_get_object

    with patch("boto3.client", return_value=mock_boto), \
         patch("app.services.s3_service.S3Service._get_repo_from_db", return_value=mock_repo):
        # 1. Put object under legacy repository (uses old_password directly)
        s3_legacy = S3Service(repo_id=repo_id)
        s3_legacy._client = mock_boto
        data = b"hostname LegacySwitch\ninterface GigabitEthernet0/1\n"
        s3_legacy.put_config_object(s3_key="configs/switch.cfg", data=data)

        # 2. Rotate master password
        repo_svc = StorageRepositoryService(mock_db)
        repo_svc.rotate_repository_password(
            repo_id,
            current_master_password=old_password,
            new_master_password=new_password,
        )

        # 3. Verify that post-rotation S3 service can restore legacy backup!
        s3_post = S3Service(repo_id=repo_id)
        s3_post._client = mock_boto
        restored = s3_post.get_config_object("configs/switch.cfg")
        assert restored == data


def test_password_rotation_validation_errors():
    """Validates policy checks, same-password check, and repo not found."""
    from app.core.errors import AppError
    from app.services.storage_repository_service import StorageRepositoryService

    mock_db = MagicMock()
    repo_svc = StorageRepositoryService(mock_db)

    # 1. Same password
    with pytest.raises(AppError) as exc_info:
        repo_svc.rotate_repository_password(
            uuid.uuid4(),
            current_master_password="Password123!",
            new_master_password="Password123!",
        )
    assert exc_info.value.code == "SAME_PASSWORD"

    # 2. Repo not found
    mock_db.scalar.return_value = None
    with pytest.raises(AppError) as exc_info:
        repo_svc.rotate_repository_password(
            uuid.uuid4(),
            current_master_password="Password123!",
            new_master_password="NewPassword456!",
        )
    assert exc_info.value.code == "REPO_NOT_FOUND"


def test_dispatch_due_backups_aborts_when_no_active_s3_storage():
    """Verify Celery Beat scheduler refuses to dispatch jobs when S3 storage is disconnected."""
    from unittest.mock import patch, MagicMock
    from app.tasks.scheduler_tasks import dispatch_due_backups

    mock_db = MagicMock()
    # Mock no active repository
    mock_db.scalar.return_value = None
    # Stale jobs query empty
    mock_db.query.return_value.filter.return_value.all.return_value = []

    with patch("app.tasks.scheduler_tasks.new_session") as mock_sess:
        mock_sess.return_value.__enter__.return_value = mock_db
        res = dispatch_due_backups()
        assert res == {"dispatched": 0}


def test_repository_device_settings_archive_and_restore():
    """Verify device settings (Driver & Schedule) are safely archived on disconnect and restored on reconnect."""
    from datetime import time
    from unittest.mock import MagicMock, patch
    from app.models.storage_repository import StorageRepository
    from app.models.device import Device
    from app.models.backup_setting import DeviceBackupSetting
    from app.models.repository_device_setting_archive import RepositoryDeviceSettingArchive
    from app.services.storage_repository_service import StorageRepositoryService

    mock_db = MagicMock()
    repo_svc = StorageRepositoryService(mock_db)

    repo = StorageRepository(
        id=uuid.uuid4(),
        name="Ceph S3 Vault",
        endpoint="https://s3.example.com",
        bucket="network-backup",
        access_key="test_acc",
        secret_key_encrypted="enc_sec",
        master_key_encrypted="enc_mast",
        is_active=True,
        repo_manifest={"dek": "test_dek_32bytes_value_12345678"},
    )

    dev = Device(id=1, hostname="Switch-01", zabbix_host_id="z1", host_group="Core", ip_address="10.0.0.1")
    setting = DeviceBackupSetting(
        device_id=1,
        driver_key="ruijie-switch",
        schedule_enabled=True,
        daily_time=time(3, 0),
        retention_policy="standard_31",
    )

    mock_db.query.return_value.join.return_value.all.return_value = [(setting, dev)]
    mock_db.scalar.return_value = None  # No existing archive row

    with patch("app.services.storage_repository_service.decrypt_secret", return_value="secret"), \
         patch("app.services.storage_repository_service.S3Service") as MockS3:
        mock_s3_instance = MagicMock()
        MockS3.return_value = mock_s3_instance

        # 1. Test saving / archiving
        count = repo_svc.save_repository_device_settings(repo)
        assert count == 1
        assert mock_db.add.called
        assert mock_s3_instance.put_repo_settings.called

        # 2. Test clearing active settings on disconnect
        repo_svc.clear_active_device_settings()
        assert mock_db.query.return_value.update.called

        # 3. Test restoring settings on reconnect
        mock_s3_instance.has_repo_settings.return_value = False  # Test fallback to DB archive
        archive_row = RepositoryDeviceSettingArchive(
            s3_bucket="network-backup",
            device_hostname="Switch-01",
            device_zabbix_id="z1",
            driver_key="ruijie-switch",
            schedule_enabled=True,
            daily_time=time(3, 0),
            retention_policy="standard_31",
        )
        mock_db.scalars.return_value.all.return_value = [archive_row]
        mock_db.scalar.side_effect = [dev, setting]

        restored = repo_svc.reconcile_repository_settings(repo)
        assert restored == 1
        assert setting.driver_key == "ruijie-switch"
        assert setting.schedule_enabled is True
        assert setting.daily_time == time(3, 0)





