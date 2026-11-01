from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_repo_manifest,
    decrypt_secret,
    encrypt_secret,
    validate_password_policy,
    verify_and_read_repo_manifest,
)
from app.crypto.payload_crypto import decrypt_payload_aes256, encrypt_payload_aes256
from app.models.backup_job import BackupJob
from app.models.backup_setting import DeviceBackupSetting
from app.models.config_object import ConfigObject
from app.models.device import Device
from app.models.repository_device_setting_archive import RepositoryDeviceSettingArchive
from app.models.snapshot import Snapshot
from app.models.storage_repository import StorageRepository
from app.services.s3_service import S3Service, S3ServiceError

logger = logging.getLogger(__name__)


class StorageRepositoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def test_connection(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        secure: bool,
    ) -> dict[str, Any]:
        """
        Tests S3 connectivity, validates bucket reachability, and detects
        whether this bucket is an uninitialized (empty) bucket or an existing repo.
        """
        # Enforce SSL Certificate verification for HTTPS endpoints
        if endpoint.strip().lower().startswith("https://") and not secure:
            return {
                "success": False,
                "endpoint": endpoint,
                "bucket": bucket,
                "has_manifest": False,
                "is_empty_repo": True,
                "message": "SSL Certificate Validation is required for HTTPS endpoints. Please enable Verify SSL / TLS Certificate.",
            }

        pin_details = None
        if endpoint.strip().lower().startswith("https://") and secure:
            from app.services.ssl_cert_service import auto_trust_endpoint_certificate
            try:
                pin_details = auto_trust_endpoint_certificate(endpoint.strip())
            except Exception as exc:
                logger.warning("SSL certificate auto-trust check failed for %s: %s", endpoint, exc)

        try:
            s3 = S3Service(
                endpoint_url=endpoint.strip(),
                bucket_name=bucket.strip(),
                access_key=access_key.strip(),
                secret_key=secret_key.strip(),
                verify_ssl=secure,
            )
            # 1. Validate bucket reachability and credentials
            s3.validate_connection()
            # 2. Check if repo manifest exists
            has_manifest = s3.has_repo_manifest()
            msg = (
                "Connection successful: Existing repository manifest detected."
                if has_manifest
                else "Connection successful: Empty or uninitialized bucket detected."
            )
            if pin_details and pin_details.get("action") == "pinned":
                msg += f" SSL certificate auto-verified & pinned (SHA-256: {pin_details['fingerprint']})."

            return {
                "success": True,
                "endpoint": endpoint.strip(),
                "bucket": bucket.strip(),
                "has_manifest": has_manifest,
                "manifest_exists": has_manifest,
                "is_empty_repo": not has_manifest,
                "pinned_certificate": pin_details,
                "message": msg,
            }
        except Exception as exc:
            logger.warning("S3 connection test failed: %s", exc)
            return {
                "success": False,
                "endpoint": endpoint.strip(),
                "bucket": bucket.strip(),
                "has_manifest": False,
                "is_empty_repo": True,
                "message": f"S3 connection failed: {exc}",
            }

    def initialize_repository(
        self,
        *,
        name: str,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        secure: bool,
        master_password: str,
    ) -> StorageRepository:
        """
        Initializes a brand new repository in S3.
        Creates encrypted repo_manifest.enc in S3 using master_password,
        saves to DB, and activates it.
        """
        validate_password_policy(master_password)

        if endpoint.strip().lower().startswith("https://"):
            if not secure:
                raise AppError(
                    status_code=400,
                    code="SSL_VERIFICATION_REQUIRED",
                    message="SSL Certificate Validation is required for HTTPS endpoints. Please enable Verify SSL / TLS Certificate.",
                )
            from app.services.ssl_cert_service import auto_trust_endpoint_certificate
            try:
                auto_trust_endpoint_certificate(endpoint.strip())
            except Exception as exc:
                logger.warning("SSL auto-trust failed during initialize_repository: %s", exc)

        # 1. Connect to S3
        s3 = S3Service(
            endpoint_url=endpoint,
            bucket_name=bucket,
            access_key=access_key,
            secret_key=secret_key,
            verify_ssl=secure,
        )

        # SEC-01: Prohibit re-initialization if a manifest already exists in the bucket
        try:
            if s3.has_repo_manifest():
                raise AppError(
                    status_code=409,
                    code="REPOSITORY_ALREADY_INITIALIZED",
                    message=(
                        "Repository manifest already exists in the target S3 bucket. "
                        "Re-initializing would overwrite the encryption verifier and permanently destroy "
                        "access to all existing backups. Please use 'Unlock Existing Repository' instead."
                    ),
                )
        except S3ServiceError as exc:
            raise AppError(
                status_code=400,
                code="S3_CONNECTION_FAILED",
                message=f"Failed to verify S3 repository state: {exc}",
            )

        repo_id = uuid.uuid4()
        manifest_bytes = create_repo_manifest(master_password, str(repo_id))

        try:
            put_info = s3.put_repo_manifest(manifest_bytes, allow_overwrite=False)
        except S3ServiceError as exc:
            is_conflict = "already exists" in str(exc).lower() or "precondition" in str(exc).lower()
            raise AppError(
                status_code=409 if is_conflict else 500,
                code="REPOSITORY_ALREADY_INITIALIZED" if is_conflict else "S3_INIT_FAILED",
                message=f"Failed to upload repository manifest to S3: {exc}",
            )
        except Exception as exc:
            raise AppError(
                status_code=500,
                code="S3_INIT_FAILED",
                message=f"Failed to upload repository manifest to S3: {exc}",
            )

        # SEC-01: Mandatory Restore Drill before database activation
        try:
            downloaded_manifest = s3.get_repo_manifest()
        except Exception as exc:
            raise AppError(
                status_code=500,
                code="RESTORE_DRILL_FETCH_FAILED",
                message=f"Restore drill failed: Could not read back repository manifest from S3: {exc}",
            )

        try:
            verified_manifest = verify_and_read_repo_manifest(downloaded_manifest, master_password)
        except Exception as exc:
            raise AppError(
                status_code=500,
                code="RESTORE_DRILL_DECRYPT_FAILED",
                message=f"Restore drill failed: Read-back manifest could not be decrypted or verified: {exc}",
            )

        if not verified_manifest or verified_manifest.get("repo_id") != str(repo_id):
            raise AppError(
                status_code=500,
                code="RESTORE_DRILL_MISMATCH",
                message="Restore drill failed: Decrypted manifest repo_id mismatch.",
            )

        # 2. Deactivate previous active repo
        self.db.execute(
            update(StorageRepository).values(is_active=False)
        )

        # 3. Create repository record with version metadata
        enc_secret = encrypt_secret(secret_key)
        enc_master = encrypt_secret(master_password)
        repo_manifest_meta = {
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "repo_id": str(repo_id),
            "version_id": put_info.get("version_id"),
            "etag": put_info.get("etag"),
            "restore_drill_passed": True,
            "has_envelope_dek": True,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        repo = StorageRepository(
            id=repo_id,
            name=name.strip() or f"S3 Repository ({bucket})",
            endpoint=endpoint.strip(),
            bucket=bucket.strip(),
            access_key=access_key.strip(),
            secret_key_encrypted=enc_secret,
            master_key_encrypted=enc_master,
            secure=secure,
            is_active=True,
            is_initialized=True,
            repo_manifest=repo_manifest_meta,
        )
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    def unlock_and_activate(
        self,
        *,
        name: str,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        secure: bool,
        master_password: str,
    ) -> StorageRepository:
        """
        Unlocks an existing repository in S3 using its master_password.
        Verifies repo_manifest.enc from S3, saves/updates record in DB, and activates it.
        """
        if endpoint.strip().lower().startswith("https://"):
            if not secure:
                raise AppError(
                    status_code=400,
                    code="SSL_VERIFICATION_REQUIRED",
                    message="SSL Certificate Validation is required for HTTPS endpoints. Please enable Verify SSL / TLS Certificate.",
                )
            from app.services.ssl_cert_service import auto_trust_endpoint_certificate
            try:
                auto_trust_endpoint_certificate(endpoint.strip())
            except Exception as exc:
                logger.warning("SSL auto-trust failed during unlock_and_activate: %s", exc)

        s3 = S3Service(
            endpoint_url=endpoint,
            bucket_name=bucket,
            access_key=access_key,
            secret_key=secret_key,
            verify_ssl=secure,
        )

        try:
            manifest_bytes = s3.get_repo_manifest()
        except Exception as exc:
            raise AppError(
                status_code=400,
                code="REPO_MANIFEST_NOT_FOUND",
                message=f"Repository manifest file not found in S3 bucket: {exc}",
            )

        from app.core.security_errors import (
            IntegrityVerificationError,
            RepositoryManifestVerificationError,
        )
        try:
            verified = verify_and_read_repo_manifest(manifest_bytes, master_password)
        except (RepositoryManifestVerificationError, IntegrityVerificationError) as exc:
            raise AppError(
                status_code=400,
                code="INVALID_REPO_PASSWORD",
                message=f"Invalid master password or repository manifest is corrupt: {exc}",
            )

        if not verified:
            raise AppError(
                status_code=400,
                code="INVALID_REPO_PASSWORD",
                message="Invalid master password or repository manifest is corrupt.",
            )

        repo_id_str = verified.get("repo_id")
        try:
            repo_id = uuid.UUID(repo_id_str) if repo_id_str else uuid.uuid4()
        except Exception:
            repo_id = uuid.uuid4()

        # Check if already in DB
        existing = self.db.scalar(
            select(StorageRepository).where(
                (StorageRepository.id == repo_id)
                | (
                    (StorageRepository.endpoint == endpoint)
                    & (StorageRepository.bucket == bucket)
                )
            )
        )

        # Deactivate all others
        self.db.execute(update(StorageRepository).values(is_active=False))

        enc_secret = encrypt_secret(secret_key)
        enc_master = encrypt_secret(master_password)

        if existing:
            existing.name = name.strip() or existing.name
            existing.endpoint = endpoint.strip()
            existing.bucket = bucket.strip()
            existing.access_key = access_key.strip()
            existing.secret_key_encrypted = enc_secret
            existing.master_key_encrypted = enc_master
            existing.secure = secure
            existing.is_active = True
            existing.is_initialized = True
            existing.repo_manifest = verified
            repo = existing
        else:
            repo = StorageRepository(
                id=repo_id,
                name=name.strip() or f"S3 Repository ({bucket})",
                endpoint=endpoint.strip(),
                bucket=bucket.strip(),
                access_key=access_key.strip(),
                secret_key_encrypted=enc_secret,
                master_key_encrypted=enc_master,
                secure=secure,
                is_active=True,
                is_initialized=True,
                repo_manifest=verified,
            )
            self.db.add(repo)

        self.db.commit()
        self.db.refresh(repo)

        # Reconcile orphaned history matching this repository bucket
        try:
            reconciled = self.reconcile_repository_objects(repo)
            logger.info(
                "Reconciled repository %s: %d objects, %d snapshots, %d jobs restored.",
                repo.id,
                reconciled.get("config_objects", 0),
                reconciled.get("snapshots", 0),
                reconciled.get("backup_jobs", 0),
            )
        except Exception as exc:
            logger.warning("Historical reconciliation failed during unlock: %s", exc)

        # Restore per-repository device settings (Driver, Schedule)
        try:
            restored_settings = self.reconcile_repository_settings(repo)
            logger.info(
                "Restored device settings for %d devices from repository %s.",
                restored_settings,
                repo.id,
            )
        except Exception as exc:
            logger.warning("Device settings restoration failed during unlock: %s", exc)

        self.db.refresh(repo)
        return repo

    def reconcile_repository_objects(self, repo: StorageRepository) -> dict[str, int]:
        """
        Reconciles orphaned ConfigObjects, Snapshots, and BackupJobs matching
        the repository's S3 bucket, restoring historical backup continuity when
        a repository is reconnected, unlocked, or activated.
        """
        try:
            cos = (
                self.db.query(ConfigObject)
                .filter(
                    ConfigObject.s3_bucket == repo.bucket,
                    (ConfigObject.repository_id == repo.id) | (ConfigObject.repository_id.is_(None)),
                )
                .order_by(ConfigObject.id.asc())
                .all()
            )

            groups: dict[tuple[int, str], list[ConfigObject]] = {}
            for c in cos:
                key = (c.device_id, c.content_sha256)
                groups.setdefault(key, []).append(c)

            for (dev_id, sha), obj_list in groups.items():
                primary = next((o for o in obj_list if o.repository_id == repo.id), obj_list[0])
                primary.repository_id = repo.id

                for other in obj_list:
                    if other.id != primary.id:
                        try:
                            self.db.query(Snapshot).filter(Snapshot.config_object_id == other.id).update(
                                {"config_object_id": primary.id, "repository_id": repo.id},
                                synchronize_session=False,
                            )
                            self.db.delete(other)
                        except Exception as err:
                            logger.warning("Could not merge redundant config_object %s: %s", other.id, err)

            self.db.flush()

            primary_co_ids = self.db.scalars(
                select(ConfigObject.id).where(ConfigObject.repository_id == repo.id)
            ).all()
            updated_snaps = 0
            if primary_co_ids:
                updated_snaps = (
                    self.db.query(Snapshot)
                    .filter(
                        Snapshot.config_object_id.in_(primary_co_ids),
                        Snapshot.repository_id.is_(None),
                    )
                    .update({"repository_id": repo.id}, synchronize_session=False)
                )

            snap_job_ids = self.db.scalars(
                select(Snapshot.backup_job_id).where(Snapshot.repository_id == repo.id)
            ).all()
            updated_jobs = 0
            if snap_job_ids:
                updated_jobs = (
                    self.db.query(BackupJob)
                    .filter(
                        BackupJob.id.in_(snap_job_ids),
                        BackupJob.repository_id.is_(None),
                    )
                    .update({"repository_id": repo.id}, synchronize_session=False)
                )

            self.db.commit()
            return {
                "config_objects": len(groups),
                "snapshots": updated_snaps,
                "backup_jobs": updated_jobs,
            }
        except Exception as exc:
            logger.warning("Error during repository object reconciliation: %s", exc)
            self.db.rollback()
            return {"config_objects": 0, "snapshots": 0, "backup_jobs": 0}

    def save_repository_device_settings(self, repo: StorageRepository) -> int:
        """
        Snapshots current active DeviceBackupSettings into:
        1. Local database archive table (repository_device_setting_archives)
        2. S3 bucket encrypted object (repo_settings.enc)
        """
        settings_rows = (
            self.db.query(DeviceBackupSetting, Device)
            .join(Device, Device.id == DeviceBackupSetting.device_id)
            .all()
        )

        settings_payload: list[dict[str, Any]] = []
        count = 0

        for s, dev in settings_rows:
            archive_row = self.db.scalar(
                select(RepositoryDeviceSettingArchive).where(
                    RepositoryDeviceSettingArchive.s3_bucket == repo.bucket,
                    RepositoryDeviceSettingArchive.device_hostname == dev.hostname,
                )
            )
            daily_str = s.daily_time.strftime("%H:%M") if s.daily_time else None
            if not archive_row:
                archive_row = RepositoryDeviceSettingArchive(
                    s3_bucket=repo.bucket,
                    device_hostname=dev.hostname,
                    device_zabbix_id=dev.zabbix_host_id,
                    driver_key=s.driver_key,
                    schedule_enabled=s.schedule_enabled,
                    daily_time=s.daily_time,
                    retention_policy=s.retention_policy or "standard_31",
                )
                self.db.add(archive_row)
            else:
                archive_row.device_zabbix_id = dev.zabbix_host_id
                archive_row.driver_key = s.driver_key
                archive_row.schedule_enabled = s.schedule_enabled
                archive_row.daily_time = s.daily_time
                archive_row.retention_policy = s.retention_policy or "standard_31"

            settings_payload.append({
                "hostname": dev.hostname,
                "zabbix_id": dev.zabbix_host_id,
                "driver_key": s.driver_key,
                "schedule_enabled": s.schedule_enabled,
                "daily_time": daily_str,
                "retention_policy": s.retention_policy or "standard_31",
            })
            count += 1

        self.db.commit()

        # Attempt to persist encrypted settings to S3
        try:
            sec_key = decrypt_secret(repo.secret_key_encrypted)
            master_pwd = decrypt_secret(repo.master_key_encrypted) if repo.master_key_encrypted else None
            dek = repo.repo_manifest.get("dek") if repo.repo_manifest else None

            s3 = S3Service(
                endpoint_url=repo.endpoint,
                bucket_name=repo.bucket,
                access_key=repo.access_key,
                secret_key=sec_key,
                verify_ssl=repo.secure,
            )
            key_material = dek or master_pwd
            if key_material:
                json_bytes = json.dumps(settings_payload).encode("utf-8")
                encrypted = encrypt_payload_aes256(json_bytes, key_material=key_material)
                s3.put_repo_settings(encrypted)
                logger.info("Persisted encrypted repo settings for %d devices to S3 bucket %s", len(settings_payload), repo.bucket)
        except Exception as exc:
            logger.warning("Could not persist repo_settings to S3 bucket %s: %s", repo.bucket, exc)

        return count

    def reconcile_repository_settings(self, repo: StorageRepository) -> int:
        """
        Restores device backup settings (Driver & Schedule) when a repository
        is reconnected, unlocked, or activated:
        1. Attempts to read and decrypt repo_settings.enc from S3
        2. Falls back to repository_device_setting_archives in DB if S3 read fails
        """
        from app.services.backup_settings_service import BackupSettingsService

        settings_list: list[dict[str, Any]] | None = None

        # 1. Try reading from S3
        try:
            sec_key = decrypt_secret(repo.secret_key_encrypted)
            master_pwd = decrypt_secret(repo.master_key_encrypted) if repo.master_key_encrypted else None
            dek = repo.repo_manifest.get("dek") if repo.repo_manifest else None

            s3 = S3Service(
                endpoint_url=repo.endpoint,
                bucket_name=repo.bucket,
                access_key=repo.access_key,
                secret_key=sec_key,
                verify_ssl=repo.secure,
            )
            if s3.has_repo_settings():
                encrypted = s3.get_repo_settings()
                key_material = dek or master_pwd
                if key_material:
                    decrypted = decrypt_payload_aes256(encrypted, key_material=key_material)
                    settings_list = json.loads(decrypted.decode("utf-8"))
                    logger.info("Loaded %d device settings from S3 repo_settings.enc for bucket %s", len(settings_list), repo.bucket)
        except Exception as exc:
            logger.warning("Could not load repo_settings.enc from S3: %s", exc)

        # 2. Fall back to DB archive if S3 didn't yield settings
        if settings_list is None:
            db_archives = self.db.scalars(
                select(RepositoryDeviceSettingArchive).where(
                    RepositoryDeviceSettingArchive.s3_bucket == repo.bucket
                )
            ).all()
            if db_archives:
                settings_list = [
                    {
                        "hostname": a.device_hostname,
                        "zabbix_id": a.device_zabbix_id,
                        "driver_key": a.driver_key,
                        "schedule_enabled": a.schedule_enabled,
                        "daily_time": a.daily_time.strftime("%H:%M") if a.daily_time else None,
                        "retention_policy": a.retention_policy,
                    }
                    for a in db_archives
                ]
                logger.info("Loaded %d device settings from DB archive for bucket %s", len(settings_list), repo.bucket)

        if not settings_list:
            return 0

        restored = 0
        settings_service = BackupSettingsService(self.db)

        for item in settings_list:
            hostname = item.get("hostname")
            zabbix_id = item.get("zabbix_id")
            device = None
            if hostname:
                device = self.db.scalar(select(Device).where(Device.hostname == hostname))
            if not device and zabbix_id:
                device = self.db.scalar(select(Device).where(Device.zabbix_host_id == zabbix_id))
            if not device:
                continue

            setting = self.db.scalar(
                select(DeviceBackupSetting).where(DeviceBackupSetting.device_id == device.id)
            )
            if not setting:
                setting = DeviceBackupSetting(device_id=device.id)
                self.db.add(setting)

            setting.driver_key = item.get("driver_key")
            sched_enabled = bool(item.get("schedule_enabled", False))
            daily_str = item.get("daily_time")
            parsed_time = None
            if daily_str:
                try:
                    parts = daily_str.split(":")
                    parsed_time = time(int(parts[0]), int(parts[1]))
                except Exception:
                    parsed_time = None

            setting.schedule_enabled = sched_enabled
            setting.daily_time = parsed_time if sched_enabled else None
            setting.retention_policy = item.get("retention_policy") or "standard_31"
            if sched_enabled and parsed_time:
                setting.next_run_at = settings_service._next_run(parsed_time)
            else:
                setting.next_run_at = None

            restored += 1

        self.db.commit()
        return restored

    def clear_active_device_settings(self) -> int:
        """
        Clears active device backup settings when storage is disconnected or deleted:
        Disables schedules and clears driver assignments on all devices.
        """
        updated = self.db.query(DeviceBackupSetting).update(
            {
                "driver_key": None,
                "schedule_enabled": False,
                "daily_time": None,
                "next_run_at": None,
                "last_dispatched_at": None,
            },
            synchronize_session=False,
        )
        self.db.commit()
        return updated

    def activate_repository(self, repo_id: uuid.UUID) -> StorageRepository:
        repo = self.db.scalar(select(StorageRepository).where(StorageRepository.id == repo_id))
        if repo is None:
            raise AppError(status_code=404, code="REPO_NOT_FOUND", message="Storage repository not found.")

        # Archive settings of currently active repo before switching
        current_active = self.db.scalar(
            select(StorageRepository).where(StorageRepository.is_active == True, StorageRepository.id != repo_id)
        )
        if current_active:
            try:
                self.save_repository_device_settings(current_active)
            except Exception as exc:
                logger.warning("Failed to archive settings for active repo %s before switching: %s", current_active.id, exc)

        self.db.execute(update(StorageRepository).values(is_active=False))
        repo.is_active = True
        self.db.commit()
        self.db.refresh(repo)

        # Reconcile orphaned history when switching repositories
        try:
            self.reconcile_repository_objects(repo)
        except Exception as exc:
            logger.warning("Historical reconciliation encountered an issue while activating %s: %s", repo.id, exc)

        # Restore per-repository device settings (Driver, Schedule)
        try:
            self.reconcile_repository_settings(repo)
        except Exception as exc:
            logger.warning("Device settings reconciliation encountered an issue while activating %s: %s", repo.id, exc)

        self.db.refresh(repo)
        return repo

    def deactivate_all(self) -> None:
        """Disconnects / unmounts the active storage repository."""
        active_repo = self.db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
        if active_repo:
            try:
                self.save_repository_device_settings(active_repo)
            except Exception as exc:
                logger.warning("Failed to archive settings before disconnect: %s", exc)

        self.db.execute(update(StorageRepository).values(is_active=False))
        self.db.commit()

        # Detach and clear active settings so scheduler and UI are clean
        self.clear_active_device_settings()

    def delete_repository(self, repo_id: uuid.UUID) -> dict[str, Any]:
        """
        Deletes a configured storage repository from the database.
        If the repository is currently active, it is deactivated first.
        Historical snapshots and objects are retained and will be automatically
        reconnected when the repository is unlocked.
        """
        repo = self.db.query(StorageRepository).filter_by(id=repo_id).first()
        if not repo:
            raise AppError(
                status_code=404,
                code="REPOSITORY_NOT_FOUND",
                message="Storage repository not found.",
            )
        repo_name = repo.name
        was_active = repo.is_active

        # Archive settings before deleting repo
        try:
            self.save_repository_device_settings(repo)
        except Exception as exc:
            logger.warning("Failed to archive settings before deleting repo %s: %s", repo_id, exc)

        preserved_snaps = (
            self.db.scalar(
                select(func.count(Snapshot.id)).where(Snapshot.repository_id == repo_id)
            )
            or 0
        )

        # Explicitly decouple all foreign key references before deleting repository
        self.db.execute(
            update(Snapshot)
            .where(Snapshot.repository_id == repo_id)
            .values(repository_id=None)
        )
        self.db.execute(
            update(ConfigObject)
            .where(ConfigObject.repository_id == repo_id)
            .values(repository_id=None)
        )
        self.db.execute(
            update(BackupJob)
            .where(BackupJob.repository_id == repo_id)
            .values(repository_id=None)
        )
        self.db.flush()

        self.db.delete(repo)
        self.db.commit()

        # If repo was active or no remaining active repo, clear device settings
        remaining_active = self.db.scalar(
            select(StorageRepository.id).where(StorageRepository.is_active == True)
        )
        if not remaining_active:
            self.clear_active_device_settings()

        return {
            "success": True,
            "was_active": was_active,
            "message": f"Storage repository '{repo_name}' successfully removed. {preserved_snaps} historical backups preserved in S3.",
        }

    def list_repositories(self) -> list[dict[str, Any]]:
        repos = self.db.scalars(
            select(StorageRepository).order_by(StorageRepository.created_at.asc())
        ).all()

        results = []
        for r in repos:
            # Count snapshots in this repository
            snap_count = self.db.scalar(
                select(func.count(Snapshot.id)).where(Snapshot.repository_id == r.id)
            ) or 0
            
            # Mask access key for safety (e.g. PDV4****CNAE)
            ak = r.access_key
            masked_ak = f"{ak[:4]}****{ak[-4:]}" if len(ak) > 8 else "****"

            results.append({
                "id": str(r.id),
                "name": r.name,
                "endpoint": r.endpoint,
                "bucket": r.bucket,
                "access_key_masked": masked_ak,
                "secure": r.secure,
                "is_active": r.is_active,
                "is_initialized": r.is_initialized,
                "snapshot_count": snap_count,
                "created_at": r.created_at.isoformat(),
            })
        return results

    def get_active_repository(self) -> dict[str, Any] | None:
        repo = self.db.scalar(select(StorageRepository).where(StorageRepository.is_active == True))
        if not repo:
            return None
        snap_count = self.db.scalar(
            select(func.count(Snapshot.id)).where(Snapshot.repository_id == repo.id)
        ) or 0
        ak = repo.access_key
        masked_ak = f"{ak[:4]}****{ak[-4:]}" if len(ak) > 8 else "****"
        return {
            "id": str(repo.id),
            "name": repo.name,
            "endpoint": repo.endpoint,
            "bucket": repo.bucket,
            "access_key_masked": masked_ak,
            "secure": repo.secure,
            "is_active": repo.is_active,
            "is_initialized": repo.is_initialized,
            "snapshot_count": snap_count,
            "created_at": repo.created_at.isoformat(),
        }

    def rotate_repository_password(
        self,
        repo_id: uuid.UUID,
        *,
        current_master_password: str,
        new_master_password: str,
    ) -> StorageRepository:
        """
        Safely rotates the repository master password through a verified re-encryption procedure:
        1. Validates new password policy and ensures difference from current password.
        2. Fetches existing manifest from S3 and verifies current_master_password decrypts it.
        3. Encrypts a new manifest using new_master_password (preserving original repo_id).
        4. Overwrites manifest in S3 (allow_overwrite=True) and captures new version ID/ETag.
        5. Executes restore drill with new_master_password before committing to DB.
        6. Updates master_key_encrypted and manifest metadata in DB transaction.
        """
        validate_password_policy(new_master_password)
        if current_master_password == new_master_password:
            raise AppError(status_code=400, code="SAME_PASSWORD", message="New master password must be different from current password.")

        repo = self.db.scalar(
            select(StorageRepository)
            .where(StorageRepository.id == repo_id)
            .with_for_update()
        )
        if not repo:
            raise AppError(status_code=404, code="REPO_NOT_FOUND", message="Storage repository not found.")

        secret_key = decrypt_secret(repo.secret_key_encrypted)
        s3 = S3Service(
            endpoint_url=repo.endpoint,
            bucket_name=repo.bucket,
            access_key=repo.access_key,
            secret_key=secret_key,
            verify_ssl=repo.secure,
            repo_id=repo.id,
        )

        try:
            original_etag = None
            original_version_id = None
            if hasattr(s3, "get_repo_manifest_meta"):
                try:
                    meta = s3.get_repo_manifest_meta()
                    if isinstance(meta, dict) and isinstance(meta.get("data"), (bytes, bytearray)):
                        original_manifest_bytes = meta["data"]
                        original_etag = meta.get("etag")
                        original_version_id = meta.get("version_id")
                    else:
                        original_manifest_bytes = s3.get_repo_manifest()
                except Exception:
                    original_manifest_bytes = s3.get_repo_manifest()
            else:
                original_manifest_bytes = s3.get_repo_manifest()
        except Exception as exc:
            raise AppError(status_code=400, code="REPO_MANIFEST_NOT_FOUND", message=f"Could not fetch manifest from S3: {exc}")

        if not original_etag:
            raise AppError(
                status_code=400,
                code="ETAG_UNAVAILABLE",
                message="Cannot safely rotate password: repository manifest ETag is unavailable on storage engine.",
            )

        try:
            existing_manifest = verify_and_read_repo_manifest(original_manifest_bytes, current_master_password)
        except Exception as exc:
            raise AppError(status_code=400, code="INVALID_CURRENT_PASSWORD", message=f"Current master password invalid or manifest corrupt: {exc}")

        if not existing_manifest or existing_manifest.get("repo_id") != str(repo.id):
            raise AppError(status_code=400, code="REPO_ID_MISMATCH", message="Existing manifest repository ID does not match database record.")

        # Extract persistent Data Encryption Key (DEK)
        existing_dek = existing_manifest.get("dek") or existing_manifest.get("dek_hex")
        if not existing_dek:
            # Legacy repository backward compatibility:
            # Payloads were encrypted with current_master_password. Preserve current_master_password
            # as the wrapped DEK under the new master password so all historical backups remain restorable!
            existing_dek = current_master_password

        # Create new manifest re-wrapping the same persistent DEK under new_master_password (KEK)
        new_manifest_bytes = create_repo_manifest(
            new_master_password,
            repo_id=str(repo.id),
            dek=existing_dek,
        )

        manifest_written_to_s3 = False
        db_committed = False
        rotated_etag = None
        try:
            # Conditional overwrite using If-Match ETag to protect against concurrent rotations
            put_info = s3.put_repo_manifest(
                new_manifest_bytes,
                allow_overwrite=True,
                if_match=original_etag,
            )
            rotated_etag = put_info.get("etag")
            manifest_written_to_s3 = True

            # Restore drill: verify read-back manifest decrypts under new_master_password and holds identical DEK
            downloaded_new = s3.get_repo_manifest()
            verified_new = verify_and_read_repo_manifest(downloaded_new, new_master_password)
            if not verified_new or verified_new.get("repo_id") != str(repo.id):
                raise ValueError("Rotated manifest repo_id mismatch during verification.")
            if (verified_new.get("dek") or verified_new.get("dek_hex")) != existing_dek:
                raise ValueError("Rotated manifest DEK mismatch during verification.")

            # Commit new credentials and version ID to DB within atomic transaction
            repo.master_key_encrypted = encrypt_secret(new_master_password)
            manifest_meta = dict(repo.repo_manifest or {})
            manifest_meta.update({
                "rotated_at": datetime.now(timezone.utc).isoformat(),
                "version_id": put_info.get("version_id"),
                "previous_version_id": original_version_id,
                "etag": put_info.get("etag"),
                "restore_drill_passed": True,
                "has_envelope_dek": True,
            })
            repo.repo_manifest = manifest_meta
            self.db.commit()
            db_committed = True

            try:
                self.db.refresh(repo)
            except Exception as ref_exc:
                logger.warning("Post-commit refresh failed for repo %s: %s", repo.id, ref_exc)

            s3._cached_dek = existing_dek
            return repo
        except Exception as exc:
            logger.error("Master password rotation transaction failed: %s. Initiating rollback.", exc)
            # CRITICAL SAFETY: Never rollback S3 manifest if DB commit already succeeded!
            if manifest_written_to_s3 and not db_committed:
                try:
                    s3.put_repo_manifest(
                        original_manifest_bytes,
                        allow_overwrite=True,
                        if_match=rotated_etag,
                    )
                    logger.info("Rollback: Original repository manifest restored to S3.")
                except Exception as rb_exc:
                    logger.critical("Rollback failed: Could not restore original manifest to S3: %s", rb_exc)
            if not db_committed:
                self.db.rollback()
            if isinstance(exc, AppError):
                raise
            if "concurrent modification detected" in str(exc).lower() or "if-match" in str(exc).lower():
                raise AppError(status_code=409, code="CONCURRENT_MODIFICATION_DETECTED", message=f"Manifest rotation failed due to concurrent modification: {exc}")
            raise AppError(status_code=500, code="ROTATION_TRANSACTION_FAILED", message=f"Password rotation failed and was rolled back: {exc}")
