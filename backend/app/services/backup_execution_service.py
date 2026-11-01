from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.backup_lock import (
    active_job_heartbeat,
    clear_job_heartbeat,
    device_backup_lock,
    record_job_heartbeat,
)
from app.core.job_state import ACTIVE_STATES, TERMINAL_STATES
from app.drivers.base import (
    BackupDriver,
    DeviceConnectionContext,
    DriverAuthenticationError,
    DriverCollectionError,
    DriverCommandTimeoutError,
    DriverConnectionError,
    DriverConnectionTimeoutError,
    DriverError,
    DriverNormalizationError,
    DriverNotFoundError,
    DriverValidationError,
)
from app.drivers.registry import registry
from app.models.backup_job import BackupJob
from app.models.config_object import ConfigObject
from app.models.snapshot import Snapshot
from app.repositories.device_repository import DeviceRepository
from app.services.backup_job_service import BackupJobService
from app.services.notification_service import NotificationService
from app.services.s3_service import S3Service, S3ServiceError
from app.services.zabbix_service import ZabbixService

logger = logging.getLogger(__name__)


class BackupExecutionService:
    """
    End-to-end backup state-machine executor.
    Orchestrates Zabbix pre-check, Driver SSH collection, Normalization,
    Validation, Hash generation, S3 upload, and Snapshot creation.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.job_service = BackupJobService(db)
        self.devices = DeviceRepository(db)
        self.zabbix = ZabbixService(db)
        self.s3 = S3Service()
        self.notifications = NotificationService(db)

    def _record_audit_log(
        self,
        *,
        category: str,
        severity: str,
        event_type: str,
        message: str,
        job: BackupJob | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            from app.services.audit_log_service import AuditLogService
            user_id = job.requested_by if job else None
            username = None
            if user_id:
                from app.models.user import User
                u = self.db.get(User, user_id)
                if u:
                    username = u.username

            AuditLogService.record_event_standalone(
                category=category,
                severity=severity,
                event_type=event_type,
                message=message,
                user_id=user_id,
                username=username,
                details=details,
            )
        except Exception as exc:
            logger.warning("Failed to record audit log: %s", exc)

    def _fail_job(
        self,
        *,
        job: BackupJob,
        target: str,
        failure_stage: str,
        failure_code: str,
        failure_message: str,
    ) -> None:
        transient_codes = {
            "CONNECTION_TIMEOUT",
            "SSH_TRANSPORT_ERROR",
            "COMMAND_TIMEOUT",
            "S3_UPLOAD_FAILED",
            "S3_VERIFICATION_FAILED",
        }

        device = self.devices.get_by_id(job.device_id) if hasattr(self, "devices") else None
        hostname = device.hostname if device else f"Device #{job.device_id}"
        device_ip = str(device.ip_address).split("/")[0] if device and device.ip_address else "unknown"
        trig = (job.trigger_type or "manual").capitalize()

        # Check if eligible for transient retry
        if (
            target == "FAILED"
            and failure_code in transient_codes
            and (job.attempt_count or 1) < (job.max_attempts or settings.backup_max_attempts)
        ):
            try:
                delays = [
                    int(d.strip())
                    for d in settings.backup_retry_delays_seconds.split(",")
                    if d.strip().isdigit()
                ]
            except Exception:
                delays = [30, 120, 300]
            if not delays:
                delays = [30, 120, 300]

            delay_idx = min(max((job.attempt_count or 1) - 1, 0), len(delays) - 1)
            countdown = delays[delay_idx]

            try:
                self.job_service.transition(
                    job=job,
                    target="RETRYING",
                    failure_stage=failure_stage,
                    failure_code=failure_code,
                    failure_message=f"{failure_message} (Retrying in {countdown}s, attempt {job.attempt_count}/{job.max_attempts})",
                )
                from app.tasks.backup_tasks import execute_backup
                execute_backup.apply_async(args=[str(job.id)], countdown=countdown)
                logger.info(
                    "Job %s transient failure %s scheduled for retry in %ss (attempt %s/%s)",
                    job.id,
                    failure_code,
                    countdown,
                    job.attempt_count,
                    job.max_attempts,
                )
                self._record_audit_log(
                    category="BACKUP_JOB",
                    severity="WARNING",
                    event_type="BACKUP_RETRYING",
                    message=f"Backup attempt {job.attempt_count} for device '{hostname}' ({device_ip}) failed at {failure_stage}: {failure_code} - {failure_message} (Retrying in {countdown}s).",
                    job=job,
                    details={
                        "job_id": str(job.id),
                        "device_id": job.device_id,
                        "hostname": hostname,
                        "ip_address": device_ip,
                        "failure_stage": failure_stage,
                        "failure_code": failure_code,
                        "failure_message": failure_message,
                        "countdown": countdown,
                        "attempt_count": job.attempt_count,
                        "max_attempts": job.max_attempts,
                        "trigger_type": job.trigger_type,
                    },
                )
                return
            except Exception as exc:
                logger.error("Failed to transition job %s to RETRYING: %s", job.id, exc)

        clear_job_heartbeat(job.id)
        self.job_service.transition(
            job=job,
            target=target,
            failure_stage=failure_stage,
            failure_code=failure_code,
            failure_message=failure_message,
        )

        self._record_audit_log(
            category="BACKUP_JOB",
            severity="ERROR",
            event_type=f"BACKUP_FAILED_{failure_code}",
            message=f"Error when running Backup {trig} for device '{hostname}' ({device_ip}) at {failure_stage}: {failure_code} - {failure_message}",
            job=job,
            details={
                "job_id": str(job.id),
                "device_id": job.device_id,
                "hostname": hostname,
                "ip_address": device_ip,
                "failure_stage": failure_stage,
                "failure_code": failure_code,
                "failure_message": failure_message,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "trigger_type": job.trigger_type,
                "target_state": target,
            },
        )

        try:
            self.notifications.send_backup_failure_alert(job.id)
        except Exception as exc:
            logger.error("Failed to dispatch Feishu failure alert for job %s: %s", job.id, exc)


    def execute_c5(self, job_id: uuid.UUID) -> None:
        """Alias for execute to remain backwards-compatible with task definitions."""
        self.execute(job_id)

    def execute(self, job_id: uuid.UUID, password_override: str | None = None) -> None:
        job = self.job_service.get(job_id)

        # REL-04 Idempotent entry handler: skip if already in terminal state
        if job.state in TERMINAL_STATES:
            logger.info("Job %s is already in terminal state %s; skipping idempotent redelivery", job.id, job.state)
            return

        # REL-04 Heartbeat lease & state recovery: transition intermediate active states to RETRYING first
        record_job_heartbeat(job.id)
        if job.state in ACTIVE_STATES and job.state not in ("QUEUED", "RETRYING"):
            if (job.attempt_count or 0) >= (job.max_attempts or settings.backup_max_attempts):
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage=job.state,
                    failure_code="MAX_ATTEMPTS_EXCEEDED",
                    failure_message="Job interrupted during execution and maximum attempts reached.",
                )
                return
            logger.warning(
                "Recovering redelivered job %s from intermediate state %s -> RETRYING",
                job.id,
                job.state,
            )
            self.job_service.transition(job=job, target="RETRYING")

        device = self.devices.get_by_id(job.device_id)
        if device is None:
            self._fail_job(
                job=job,
                target="FAILED",
                failure_stage="PRECHECKING_ZABBIX",
                failure_code="DEVICE_NOT_FOUND",
                failure_message="Device no longer exists in application DB.",
            )
            return

        repo_id = getattr(self.s3, "repo_id", None)
        if repo_id and not job.repository_id:
            job.repository_id = repo_id

        job.attempt_count = (job.attempt_count or 0) + 1
        self.db.commit()

        with device_backup_lock(device.id, job_id=job.id) as acquired:
            if not acquired:
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage="QUEUED",
                    failure_code="CONCURRENT_BACKUP",
                    failure_message=(
                        "Another backup execution already holds the device lock."
                    ),
                )
                return

            # Stage 1: Zabbix Live Pre-check
            self.job_service.transition(
                job=job,
                target="PRECHECKING_ZABBIX",
            )

            try:
                status, checked_at = self.zabbix.get_live_availability(
                    device.zabbix_host_id
                )
            except Exception as exc:
                logger.warning("Failed live availability check for %s: %s", device.hostname, exc)
                status, checked_at = "unknown", None

            job.zabbix_status_at_start = status
            job.zabbix_checked_at = checked_at
            self.db.commit()
            self.db.refresh(job)

            if status == "down":
                self._fail_job(
                    job=job,
                    target="SKIPPED_DEVICE_DOWN",
                    failure_stage="PRECHECKING_ZABBIX",
                    failure_code="DEVICE_DOWN",
                    failure_message="Zabbix live pre-check reports device DOWN.",
                )
                return

            if status != "up":
                self._fail_job(
                    job=job,
                    target="SKIPPED_STATUS_UNKNOWN",
                    failure_stage="PRECHECKING_ZABBIX",
                    failure_code="STATUS_UNKNOWN",
                    failure_message="Fresh Zabbix availability could not be confirmed as UP.",
                )
                return

            # Stage: Storage Repository Pre-Check (Fail-Closed if S3 is disconnected)
            from app.models.storage_repository import StorageRepository
            active_repo = self.db.scalar(
                select(StorageRepository).where(StorageRepository.is_active == True)
            )
            if not active_repo:
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage="CONNECTING",
                    failure_code="STORAGE_DISCONNECTED",
                    failure_message=(
                        "S3 storage repository is disconnected. Backup execution requires an active mounted S3 repository."
                    ),
                )
                return

            try:
                self.s3.validate_connection()
            except S3ServiceError as exc:
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage="CONNECTING",
                    failure_code="STORAGE_UNAVAILABLE",
                    failure_message=f"Active S3 storage repository cannot be reached: {exc}",
                )
                return

            # Check Driver Settings
            setting = device.backup_settings
            driver_key = setting.driver_key if setting else job.driver_key
            if not driver_key:
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage="CONNECTING",
                    failure_code="DRIVER_NOT_ASSIGNED",
                    failure_message="No backup driver assigned to device.",
                )
                return

            try:
                driver: BackupDriver = registry.create(driver_key)
            except DriverNotFoundError:
                self._fail_job(
                    job=job,
                    target="FAILED",
                    failure_stage="CONNECTING",
                    failure_code="DRIVER_NOT_FOUND",
                    failure_message=f"Backup driver '{driver_key}' is not registered.",
                )
                return

            # Driver-specific default port takes precedence over global setting
            port = getattr(driver, "default_port", None) or settings.network_ssh_port

            # Prepare Connection Context: uses IP synchronized from Zabbix!
            device_ip = str(device.ip_address).split("/")[0]
            context = DeviceConnectionContext(
                device_id=device.id,
                hostname=device.hostname,
                host=device_ip,
                port=port,
                username=settings.network_ssh_username,
                password=password_override or settings.network_ssh_password,
                connect_timeout=settings.ssh_connect_timeout_seconds,
                command_timeout=settings.ssh_command_timeout_seconds,
                enable_password=settings.network_ssh_enable_password or None,
            )

            try:
                # Stage 2: Connecting
                self.job_service.transition(
                    job=job,
                    target="CONNECTING",
                )
                try:
                    driver.connect(context)
                except DriverAuthenticationError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="CONNECTING",
                        failure_code="AUTHENTICATION_FAILED",
                        failure_message=str(exc),
                    )
                    return
                except DriverConnectionTimeoutError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="CONNECTING",
                        failure_code="CONNECTION_TIMEOUT",
                        failure_message=str(exc),
                    )
                    return
                except DriverConnectionError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="CONNECTING",
                        failure_code="SSH_TRANSPORT_ERROR",
                        failure_message=str(exc),
                    )
                    return
                except Exception as exc:
                    from app.drivers.base import DriverConfigurationError
                    if isinstance(exc, DriverConfigurationError) or getattr(exc, "code", None) == "DRIVER_CONFIGURATION_ERROR":
                        self._fail_job(
                            job=job,
                            target="FAILED",
                            failure_stage="CONNECTING",
                            failure_code="DRIVER_CONFIGURATION_ERROR",
                            failure_message=str(exc),
                        )
                        return
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="CONNECTING",
                        failure_code="SSH_UNKNOWN_ERROR",
                        failure_message=f"Connection failed: {exc}",
                    )
                    return

                # Stage 3: Collecting
                self.job_service.transition(
                    job=job,
                    target="COLLECTING",
                )
                try:
                    collected = driver.collect_config()
                except DriverCommandTimeoutError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="COLLECTING",
                        failure_code="COMMAND_TIMEOUT",
                        failure_message=str(exc),
                    )
                    return
                except DriverCollectionError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="COLLECTING",
                        failure_code="COMMAND_FAILED",
                        failure_message=str(exc),
                    )
                    return
                except Exception as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="COLLECTING",
                        failure_code="COLLECTION_ERROR",
                        failure_message=f"Collection error: {exc}",
                    )
                    return

                # Stage 4: Normalizing
                self.job_service.transition(
                    job=job,
                    target="NORMALIZING",
                )
                try:
                    normalized = driver.normalize_config(collected)
                except DriverNormalizationError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="NORMALIZING",
                        failure_code="NORMALIZATION_FAILED",
                        failure_message=str(exc),
                    )
                    return
                except Exception as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="NORMALIZING",
                        failure_code="NORMALIZATION_ERROR",
                        failure_message=f"Normalization error: {exc}",
                    )
                    return

                # Stage 5: Validating
                self.job_service.transition(
                    job=job,
                    target="VALIDATING",
                )
                try:
                    driver.validate_config(collected, normalized)
                except DriverValidationError as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="VALIDATING",
                        failure_code="INVALID_CONFIG",
                        failure_message=str(exc),
                    )
                    return
                except Exception as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="VALIDATING",
                        failure_code="VALIDATION_ERROR",
                        failure_message=f"Validation error: {exc}",
                    )
                    return

                # Stage 6: Hashing
                self.job_service.transition(
                    job=job,
                    target="HASHING",
                )
                raw_bytes = collected.text.encode(collected.encoding)
                object_sha256 = hashlib.sha256(raw_bytes).hexdigest()
                content_sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

                job.content_sha256 = content_sha256
                job.raw_size_bytes = len(raw_bytes)
                job.normalized_size_bytes = len(normalized.encode("utf-8"))
                self.db.commit()

                # Determine Change Status
                repo_id = getattr(self.s3, "repo_id", None)
                last_snapshot_stmt = (
                    select(Snapshot)
                    .options(selectinload(Snapshot.config_object))
                    .where(
                        Snapshot.device_id == device.id,
                        Snapshot.is_retained == True,
                        (Snapshot.repository_id == repo_id) if repo_id is not None else Snapshot.repository_id.is_(None),
                    )
                    .order_by(Snapshot.captured_at.desc())
                    .limit(1)
                )
                last_snapshot = self.db.scalar(last_snapshot_stmt)
                if last_snapshot is None and repo_id is not None:
                    fallback_stmt = (
                        select(Snapshot)
                        .options(selectinload(Snapshot.config_object))
                        .join(ConfigObject, Snapshot.config_object_id == ConfigObject.id)
                        .where(
                            Snapshot.device_id == device.id,
                            Snapshot.is_retained == True,
                            ConfigObject.s3_bucket == self.s3.bucket_name,
                        )
                        .order_by(Snapshot.captured_at.desc())
                        .limit(1)
                    )
                    fallback_snap = self.db.scalar(fallback_stmt)
                    if fallback_snap:
                        last_snapshot = fallback_snap
                        if fallback_snap.repository_id is None:
                            fallback_snap.repository_id = repo_id
                            if fallback_snap.config_object and fallback_snap.config_object.repository_id is None:
                                fallback_snap.config_object.repository_id = repo_id
                            self.db.commit()

                now = datetime.now(timezone.utc)
                clean_hostname = re.sub(r"[^a-zA-Z0-9_\-]", "_", device.hostname)
                timestamp_str = now.strftime("%Y%m%d_%H%M%S")
                display_filename = (
                    collected.filename
                    if getattr(collected, "filename", None)
                    else f"{clean_hostname}_{timestamp_str}.{collected.extension}"
                )
                retention_policy = (
                    setting.retention_policy if setting else "standard_31"
                )

                if last_snapshot is None:
                    change_status = "baseline"
                elif last_snapshot.config_object.content_sha256 == content_sha256:
                    target_obj = last_snapshot.config_object
                    is_obj_valid = False
                    if target_obj and target_obj.storage_status in ("available", "pending_delete"):
                        try:
                            decrypted_data = self.s3.get_config_object(target_obj.s3_key)
                            if hashlib.sha256(decrypted_data).hexdigest() == target_obj.object_sha256:
                                # Semantic verification: normalize plaintext through driver and verify content_sha256
                                try:
                                    decrypted_text = decrypted_data.decode(collected.encoding, errors="replace")
                                    if hashlib.sha256(driver.normalize_config(decrypted_text).encode("utf-8")).hexdigest() == content_sha256:
                                        is_obj_valid = True
                                    else:
                                        logger.warning(
                                            "Deduplication target object %s semantic content hash mismatch for device %s",
                                            target_obj.s3_key,
                                            device.id,
                                        )
                                        is_obj_valid = False
                                except Exception:
                                    is_obj_valid = True
                            else:
                                logger.warning(
                                    "Deduplication target object %s object hash mismatch in S3 for device %s",
                                    target_obj.s3_key,
                                    device.id,
                                )
                        except Exception as exc:
                            logger.warning(
                                "Cryptographic validation failed for deduplication object %s: %s",
                                getattr(target_obj, "s3_key", None),
                                exc,
                            )
                            is_obj_valid = False

                    if is_obj_valid:
                        change_status = "no_change"
                        # Atomically resurrect/unstage object if it was pending deletion
                        target_obj.storage_status = "available"
                        target_obj.deleted_at = None
                        target_obj.verified_at = now
                    else:
                        logger.warning(
                            "Deduplication target object %s corrupt or missing in S3 for device %s; forcing re-upload and replacement",
                            getattr(target_obj, "s3_key", None),
                            device.id,
                        )
                        change_status = "changed"
                else:
                    change_status = "changed"

                job.change_status = change_status
                self.db.commit()

                if change_status == "no_change":
                    # Deduplication: reuse verified physical ConfigObject
                    snapshot = Snapshot(
                        device_id=device.id,
                        backup_job_id=job.id,
                        config_object_id=last_snapshot.config_object_id,
                        repository_id=repo_id,
                        captured_at=now,
                        change_status="no_change",
                        retention_policy_at_capture=retention_policy,
                        display_filename=display_filename,
                        is_retained=True,
                    )
                    self.db.add(snapshot)
                    self.db.commit()

                    clear_job_heartbeat(job.id)
                    self.job_service.transition(
                        job=job,
                        target="SUCCESS_NO_CHANGE",
                    )
                    self._record_audit_log(
                        category="BACKUP_JOB",
                        severity="INFO",
                        event_type="BACKUP_SUCCESS",
                        message=f"Backup execution succeeded for device '{device.hostname}' ({device_ip}): No changes detected (Configuration deduplicated, Snapshot #{snapshot.id}).",
                        job=job,
                        details={
                            "job_id": str(job.id),
                            "device_id": device.id,
                            "hostname": device.hostname,
                            "ip_address": device_ip,
                            "status": "SUCCESS_NO_CHANGE",
                            "snapshot_id": snapshot.id,
                            "duration_ms": job.duration_ms,
                            "trigger_type": job.trigger_type,
                        },
                    )
                    return

                # Stage 7: Uploading to S3
                self.job_service.transition(
                    job=job,
                    target="UPLOADING",
                )

                try:
                    # Check if ConfigObject with (device_id, content_sha256) exists
                    existing_obj_stmt = (
                        select(ConfigObject)
                        .where(
                            ConfigObject.device_id == device.id,
                            ConfigObject.content_sha256 == content_sha256,
                            (
                                (ConfigObject.repository_id == repo_id)
                                | (
                                    ConfigObject.repository_id.is_(None)
                                    & (ConfigObject.s3_bucket == self.s3.bucket_name)
                                )
                            ),
                        )
                        .order_by(ConfigObject.id.asc())
                        .limit(1)
                    )
                    config_obj = self.db.scalar(existing_obj_stmt)
                    if config_obj and config_obj.repository_id is None and repo_id is not None:
                        config_obj.repository_id = repo_id
                        self.db.commit()

                    needs_upload = False
                    if config_obj is None:
                        needs_upload = True
                        s3_key = (
                            f"network-config/{device.id}/objects/{content_sha256}.{collected.extension}"
                        )
                    else:
                        # REL-03: Verify if existing S3 object is intact and decryptable
                        try:
                            decrypted = self.s3.get_config_object(config_obj.s3_key)
                            if hashlib.sha256(decrypted).hexdigest() != config_obj.object_sha256:
                                needs_upload = True
                        except Exception:
                            needs_upload = True

                        if needs_upload:
                            # Replace missing/corrupt object with new object version/key
                            version_ts = int(now.timestamp())
                            s3_key = (
                                f"network-config/{device.id}/objects/{content_sha256}_{version_ts}.{collected.extension}"
                            )
                            logger.info(
                                "Replacing missing or corrupt S3 object for device %s with key %s",
                                device.id,
                                s3_key,
                            )
                        else:
                            s3_key = config_obj.s3_key

                    if needs_upload:
                        upload_res = self.s3.put_config_object(
                            s3_key=s3_key,
                            data=raw_bytes,
                        )
                        if config_obj is None:
                            config_obj = ConfigObject(
                                device_id=device.id,
                                repository_id=repo_id,
                                content_sha256=content_sha256,
                                object_sha256=object_sha256,
                                s3_bucket=self.s3.bucket_name,
                                s3_key=s3_key,
                                extension=collected.extension,
                                size_bytes=len(raw_bytes),
                                etag=str(upload_res.get("etag", "")),
                                storage_status="available",
                                uploaded_at=now,
                            )
                            self.db.add(config_obj)
                        else:
                            config_obj.s3_key = s3_key
                            config_obj.s3_bucket = self.s3.bucket_name
                            config_obj.etag = str(upload_res.get("etag", ""))
                            config_obj.storage_status = "available"
                            config_obj.deleted_at = None
                            config_obj.uploaded_at = now
                            config_obj.size_bytes = len(raw_bytes)
                            config_obj.object_sha256 = object_sha256
                        self.db.commit()
                        self.db.refresh(config_obj)
                    else:
                        # Existing object was verified intact in S3: unstage if it was pending deletion
                        if config_obj.storage_status != "available" or config_obj.deleted_at is not None:
                            config_obj.storage_status = "available"
                            config_obj.deleted_at = None
                            config_obj.verified_at = now
                            self.db.commit()
                            self.db.refresh(config_obj)
                except Exception as exc:
                    from app.core.security_errors import (
                        CredentialDecryptionError,
                        EncryptionError,
                        IntegrityVerificationError,
                    )
                    cause = exc.__cause__ or exc
                    exc_str = str(exc)
                    if isinstance(cause, CredentialDecryptionError) or "Master credential decryption failed" in exc_str:
                        stage = "ENCRYPTING"
                        code = "CREDENTIAL_DECRYPTION_FAILED"
                    elif isinstance(cause, IntegrityVerificationError) or "integrity verification failed" in exc_str:
                        stage = "ENCRYPTING"
                        code = "INTEGRITY_VERIFICATION_FAILED"
                    elif isinstance(cause, EncryptionError) or "Payload encryption failed" in exc_str:
                        stage = "ENCRYPTING"
                        code = "ENCRYPTION_FAILED"
                    else:
                        stage = "UPLOADING"
                        code = "S3_UPLOAD_FAILED"

                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage=stage,
                        failure_code=code,
                        failure_message=f"Failed during upload/encryption: {exc}",
                    )
                    return

                # Stage 8: Verifying
                self.job_service.transition(
                    job=job,
                    target="VERIFYING",
                )
                try:
                    # REL-03: Full cryptographic verification: GET -> HMAC verify -> Decrypt -> Plaintext object_sha256
                    verified_data = self.s3.get_config_object(config_obj.s3_key)
                    if hashlib.sha256(verified_data).hexdigest() != config_obj.object_sha256:
                        self._fail_job(
                            job=job,
                            target="FAILED",
                            failure_stage="VERIFYING",
                            failure_code="INTEGRITY_VERIFICATION_FAILED",
                            failure_message="Cryptographic verification failed: raw object SHA-256 mismatch after download/decrypt.",
                        )
                        return

                    # Semantic content verification: normalize plaintext and compare with content_sha256
                    try:
                        verified_text = verified_data.decode(collected.encoding, errors="replace")
                        if hashlib.sha256(driver.normalize_config(verified_text).encode("utf-8")).hexdigest() != content_sha256:
                            self._fail_job(
                                job=job,
                                target="FAILED",
                                failure_stage="VERIFYING",
                                failure_code="INTEGRITY_VERIFICATION_FAILED",
                                failure_message="Cryptographic verification failed: normalized semantic content SHA-256 mismatch.",
                            )
                            return
                    except Exception as sem_err:
                        logger.debug("Semantic content verification skipped: %s", sem_err)
                except Exception as exc:
                    self._fail_job(
                        job=job,
                        target="FAILED",
                        failure_stage="VERIFYING",
                        failure_code="S3_VERIFICATION_FAILED",
                        failure_message=f"Error cryptographically verifying object in S3: {exc}",
                    )
                    return

                config_obj.verified_at = datetime.now(timezone.utc)
                config_obj.storage_status = "available"
                self.db.commit()

                # Create Snapshot
                snapshot = Snapshot(
                    device_id=device.id,
                    backup_job_id=job.id,
                    config_object_id=config_obj.id,
                    repository_id=repo_id,
                    captured_at=now,
                    change_status=change_status,
                    retention_policy_at_capture=retention_policy,
                    display_filename=display_filename,
                    is_retained=True,
                )
                self.db.add(snapshot)
                self.db.commit()

                # Stage 9: Success Changed
                clear_job_heartbeat(job.id)
                self.job_service.transition(
                    job=job,
                    target="SUCCESS_CHANGED",
                )
                self._record_audit_log(
                    category="BACKUP_JOB",
                    severity="INFO",
                    event_type="BACKUP_SUCCESS",
                    message=f"Backup execution succeeded for device '{device.hostname}' ({device_ip}): Configuration changed and archived (Snapshot #{snapshot.id}).",
                    job=job,
                    details={
                        "job_id": str(job.id),
                        "device_id": device.id,
                        "hostname": device.hostname,
                        "ip_address": device_ip,
                        "status": "SUCCESS_CHANGED",
                        "snapshot_id": snapshot.id,
                        "duration_ms": job.duration_ms,
                        "trigger_type": job.trigger_type,
                    },
                )

            finally:
                try:
                    driver.cleanup()
                except Exception as exc:
                    logger.warning("Error during driver cleanup: %s", exc)
