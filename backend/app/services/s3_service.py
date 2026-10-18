from __future__ import annotations

import io
import logging
from typing import Any, BinaryIO
import urllib3
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError

from app.config import settings
from app.core.security_logging import log_security_event

urllib3.disable_warnings()
logger = logging.getLogger(__name__)

REPO_MANIFEST_KEY = "repo_manifest.enc"


class S3ServiceError(Exception):
    pass


class S3Service:
    """
    Ceph RGW / S3 client for storing and retrieving immutable network config objects.
    Dynamically loads credentials from the active StorageRepository in DB,
    falling back to .env settings if none configured.
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket_name: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        verify_ssl: bool | None = None,
        repo_id: str | None = None,
    ) -> None:
        if endpoint_url and bucket_name and access_key and secret_key is not None:
            self.endpoint_url = endpoint_url
            self.bucket_name = bucket_name
            self.access_key = access_key
            self.secret_key = secret_key
            self.verify_ssl = verify_ssl if verify_ssl is not None else settings.s3_secure
            self.repo_id = repo_id
        self._cached_dek: str | None = None
        if not (endpoint_url and bucket_name and access_key and secret_key is not None):
            # Attempt to resolve from DB by repo_id or active StorageRepository
            repo = self._get_repo_from_db(repo_id)
            if repo:
                self.endpoint_url = repo.endpoint
                self.bucket_name = repo.bucket
                self.access_key = repo.access_key
                if getattr(repo, "secret_key_encrypted", None):
                    from app.core.security import decrypt_secret
                    from app.core.security_errors import CredentialDecryptionError
                    try:
                        self.secret_key = decrypt_secret(repo.secret_key_encrypted)
                    except CredentialDecryptionError as exc:
                        logger.error("Failed to decrypt S3 secret key for repository %s", repo.id)
                        self.secret_key = ""
                else:
                    self.secret_key = settings.s3_secret_key
                self.verify_ssl = repo.secure
                self.repo_id = repo.id
            else:
                # If no active repository exists in DB: check if storage repos are managed in DB.
                # If repos exist in DB but none is active, storage has been disconnected by user.
                has_repos = self._has_any_repo_in_db()
                if has_repos or not settings.s3_endpoint or not settings.s3_bucket:
                    self.endpoint_url = None
                    self.bucket_name = None
                    self.access_key = None
                    self.secret_key = None
                    self.verify_ssl = False
                    self.repo_id = None
                else:
                    self.endpoint_url = settings.s3_endpoint
                    self.bucket_name = settings.s3_bucket
                    self.access_key = settings.s3_access_key
                    self.secret_key = settings.s3_secret_key
                    self.verify_ssl = settings.s3_secure
                    self.repo_id = None

        if not self.endpoint_url or not self.bucket_name or not self.access_key or not self.secret_key:
            self._client = None
            return

        verify_opt: bool | str = self.verify_ssl
        if self.verify_ssl:
            from app.services.ssl_cert_service import ensure_ca_bundle
            try:
                verify_opt = ensure_ca_bundle()
            except Exception as exc:
                logger.warning("Failed to resolve dynamic CA bundle, falling back to system CAs: %s", exc)
                verify_opt = True

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            verify=verify_opt,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=5,
                read_timeout=10,
            ),
        )

    @staticmethod
    def _get_repo_from_db(repo_id: str | None = None):
        try:
            from app.database import new_session
            from app.models.storage_repository import StorageRepository
            with new_session() as db:
                if repo_id:
                    # Explicit repo ID may resolve inactive repository (e.g. retention policy)
                    return db.query(StorageRepository).filter_by(id=repo_id).first()
                return db.query(StorageRepository).filter_by(is_active=True).first()
        except Exception:
            return None

    @staticmethod
    def _has_any_repo_in_db() -> bool:
        try:
            from app.database import new_session
            from app.models.storage_repository import StorageRepository
            with new_session() as db:
                return db.query(StorageRepository).first() is not None
        except Exception:
            return False

    def get_encryption_dek(self, master_password: str) -> str:
        """
        Resolves the repository Data Encryption Key (DEK).
        Envelope encryption model:
        - Master password acts as KEK (Key Encryption Key) wrapping the repository DEK inside repo_manifest.enc.
        - DEK is a persistent random 256-bit symmetric key that encrypts all backup payloads in S3.
        - Master password rotation re-wraps the DEK in the manifest without invalidating existing payloads.
        - Fail-closed: network or manifest verification failures raise S3ServiceError, preventing upload with KEK.
        - Falls back to master_password ONLY if manifest was successfully verified and explicitly lacks DEK (legacy repository).
        """
        if getattr(self, "_cached_dek", None):
            return self._cached_dek

        from app.core.security import verify_and_read_repo_manifest

        try:
            manifest_bytes = self.get_repo_manifest()
        except Exception as exc:
            logger.error("Failed to fetch repository manifest from S3 for DEK resolution: %s", exc)
            raise S3ServiceError(f"Repository manifest cannot be retrieved from S3 for DEK resolution: {exc}") from exc

        try:
            manifest = verify_and_read_repo_manifest(manifest_bytes, master_password)
        except Exception as exc:
            logger.error("Repository manifest integrity or HMAC verification failed: %s", exc)
            raise S3ServiceError(f"Repository manifest verification or HMAC integrity failed: {exc}") from exc

        dek = manifest.get("dek") or manifest.get("dek_hex")
        if dek:
            self._cached_dek = dek
            return dek

        # Legitimate verified legacy repository manifest without envelope DEK
        logger.info("Manifest verified: legacy repository without envelope DEK. Using legacy master key.")
        self._cached_dek = master_password
        return master_password

    def put_config_object(
        self,
        *,
        s3_key: str,
        data: bytes,
        content_type: str = "text/plain",
    ) -> dict[str, str | int]:
        if not self._client or not self.bucket_name:
            raise S3ServiceError("S3 storage is not connected. Please configure and mount S3 via S3 Management.")

        # Zero-Trust Payload Encryption (AES-256-CBC + HMAC-SHA256)
        repo = self._get_repo_from_db(self.repo_id)
        if repo is None:
            log_security_event(
                event_code="SEC_PAYLOAD_ENCRYPT_FAILED",
                component="s3_service",
                operation="put_config_object",
                result="FAILURE",
                error_class="S3ServiceError",
                details="Repository configuration cannot be resolved for upload",
            )
            raise S3ServiceError("Repository configuration cannot be resolved for encrypted payload upload.")

        if not getattr(repo, "master_key_encrypted", None):
            log_security_event(
                event_code="SEC_PAYLOAD_ENCRYPT_FAILED",
                component="s3_service",
                operation="put_config_object",
                result="FAILURE",
                repository_id=str(repo.id) if getattr(repo, "id", None) else None,
                error_class="S3ServiceError",
                details="Repository master credential is missing for upload",
            )
            raise S3ServiceError("Repository master credential is missing for encrypted payload upload.")

        from app.core.security import decrypt_secret, encrypt_payload_aes256
        from app.core.security_errors import CredentialDecryptionError, EncryptionError

        try:
            master_password = decrypt_secret(repo.master_key_encrypted)
        except CredentialDecryptionError as exc:
            logger.error("Failed to decrypt repo master key: %s", exc.__class__.__name__)
            raise S3ServiceError(f"Master credential decryption failed for repository: {exc}") from exc

        dek = self.get_encryption_dek(master_password)

        try:
            payload_to_upload = encrypt_payload_aes256(data, dek)
        except EncryptionError as exc:
            logger.error("Failed to encrypt backup payload with repo DEK: %s", exc.__class__.__name__)
            raise S3ServiceError(f"Payload encryption failed: {exc}") from exc

        try:
            response = self._client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=payload_to_upload,
                ContentType=content_type,
            )
            etag = response.get("ETag", "").strip('"')
            return {
                "s3_bucket": self.bucket_name,
                "s3_key": s3_key,
                "etag": etag,
                "size_bytes": len(payload_to_upload),
            }
        except ClientError as exc:
            logger.error("Failed to upload object to S3 (%s): %s", s3_key, exc)
            raise S3ServiceError(f"S3 upload failed for {s3_key}: {exc}") from exc

    def validate_connection(self) -> None:
        if not self._client or not self.bucket_name:
            raise S3ServiceError("S3 storage client is not configured.")
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            error_msg = exc.response.get("Error", {}).get("Message") or str(exc)
            logger.error("Bucket validation failed for '%s': %s", self.bucket_name, exc)
            raise S3ServiceError(f"S3 connection failed ({error_code}): {error_msg}") from exc

    def object_exists(self, s3_key: str) -> bool:
        if not self._client or not self.bucket_name:
            return False
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            logger.error("Error checking object existence for %s: %s", s3_key, exc)
            raise S3ServiceError(f"Failed to access S3 object '{s3_key}': {exc}") from exc

    def delete_object(self, s3_key: str, bucket: str | None = None) -> bool:
        b = bucket or self.bucket_name
        if not self._client or not b:
            return False
        try:
            self._client.delete_object(Bucket=b, Key=s3_key)
            return True
        except ClientError as exc:
            logger.error("Failed to delete S3 object %s: %s", s3_key, exc)
            return False

    @staticmethod

    def _is_positively_identified_legacy(s3_key: str, raw: bytes) -> bool:
        """
        Positively identifies a legacy pre-encryption configuration object.
        Preserves legacy compatibility ONLY when:
        1. Raw bytes are non-empty and verifiable text (not a binary encrypted envelope).
        2. Corresponding DB ConfigObject exists and its object_sha256 strictly matches raw SHA-256.
        """
        if not raw:
            return False

        # Encrypted envelopes have 64 bytes of random binary salt/IV/MAC containing null bytes and non-ASCII codes.
        # Plaintext network configs never contain null bytes (\x00).
        if b"\x00" in raw[:64]:
            return False

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except Exception:
                return False

        sample = text[:256]
        if sample:
            printable_ratio = sum(1 for c in sample if c.isprintable() or c in "\r\n\t") / len(sample)
            if printable_ratio < 0.95:
                return False

        try:
            import hashlib
            from app.database import new_session
            from app.models.config_object import ConfigObject

            with new_session() as db:
                obj = db.query(ConfigObject).filter_by(s3_key=s3_key).first()
                if not obj:
                    return False
                raw_hash = hashlib.sha256(raw).hexdigest()
                return raw_hash == obj.object_sha256
        except Exception:
            return False

    def get_config_object(self, s3_key: str) -> bytes:
        if not self._client or not self.bucket_name:
            raise S3ServiceError("S3 storage is not connected. Please configure and mount S3 via S3 Management.")
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=s3_key)
            raw = response["Body"].read()

            repo = self._get_repo_from_db(self.repo_id)
            if repo and getattr(repo, "master_key_encrypted", None):
                from app.core.security import decrypt_secret, decrypt_payload_aes256
                from app.core.security_errors import (
                    CredentialDecryptionError,
                    DecryptionError,
                    IntegrityVerificationError,
                )
                try:
                    master_password = decrypt_secret(repo.master_key_encrypted)
                except CredentialDecryptionError as exc:
                    logger.error("Failed to decrypt repo master key for download: %s", exc.__class__.__name__)
                    raise S3ServiceError(f"Master credential decryption failed for repository: {exc}") from exc

                dek = self.get_encryption_dek(master_password)

                try:
                    return decrypt_payload_aes256(raw, dek)
                except (IntegrityVerificationError, DecryptionError) as exc:
                    # If DEK decryption failed and DEK differs from master_password,
                    # attempt master_password for legacy payloads captured before envelope migration.
                    if dek != master_password:
                        try:
                            return decrypt_payload_aes256(raw, master_password)
                        except Exception:
                            pass
                    # If decryption failed, check if this object is an explicitly identified legacy plaintext object
                    if self._is_positively_identified_legacy(s3_key, raw):
                        return raw
                    logger.error("Cryptographic verification/decryption failed for S3 object %s: %s", s3_key, exc.__class__.__name__)
                    raise S3ServiceError(f"Payload decryption or integrity verification failed for {s3_key}: {exc}") from exc

            # If repo or master_key_encrypted is missing, check whether data is explicitly positively identified legacy plaintext
            if self._is_positively_identified_legacy(s3_key, raw):
                return raw

            # Fail closed: never return raw object when master key or repo is missing
            if not repo:
                raise S3ServiceError("Repository configuration cannot be resolved for encrypted payload download.")
            raise S3ServiceError("Repository master credential is missing for encrypted payload download.")
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to download object from S3 (%s): %s", s3_key, exc)
            raise S3ServiceError(f"S3 download failed for {s3_key}: {exc}") from exc

    # --- Repository Manifest Management ---

    def has_repo_manifest(self) -> bool:
        return self.object_exists(REPO_MANIFEST_KEY)

    def put_repo_manifest(
        self,
        data: bytes,
        allow_overwrite: bool = False,
        if_match: str | None = None,
    ) -> dict[str, Any]:
        if not self._client or not self.bucket_name:
            raise S3ServiceError("S3 storage is not connected. Please configure and mount S3 via S3 Management.")

        # Guard: Manifest overwrite protection (SEC-01)
        if not allow_overwrite and self.has_repo_manifest():
            logger.error("Precondition failed: repository manifest already exists on bucket %s", self.bucket_name)
            raise S3ServiceError(
                "Repository manifest already exists in the bucket. Overwrite prohibited to prevent loss of restore capability."
            )

        put_kwargs: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": REPO_MANIFEST_KEY,
            "Body": data,
            "ContentType": "application/octet-stream",
        }

        try:
            response = None
            if not allow_overwrite:
                # Conditional create using If-None-Match to prevent concurrent race condition writes
                try:
                    response = self._client.put_object(**put_kwargs, IfNoneMatch="*")
                except ClientError as exc:
                    err_code = str(exc.response.get("Error", {}).get("Code", ""))
                    if err_code in ("PreconditionFailed", "412", "AtLeastOneConditionFailed"):
                        logger.error("Conditional put_object rejected by S3: %s", exc)
                        raise S3ServiceError(
                            "Repository manifest already exists (conditional write precondition failed). Overwrite prohibited."
                        ) from exc
                    if err_code in ("InvalidArgument", "NotImplemented", "UnsupportedHeader"):
                        logger.error("S3 storage engine does not support conditional PutObject (If-None-Match): %s", exc)
                        raise S3ServiceError(
                            "S3 storage engine does not support conditional PutObject (If-None-Match). Operation rejected to prevent race conditions."
                        ) from exc
                    raise
            else:
                if not if_match:
                    raise S3ServiceError("Conditional ETag precondition (If-Match) is required when updating repository manifest.")

                clean_etag = if_match.strip('"')
                if not clean_etag:
                    raise S3ServiceError("Invalid ETag provided for conditional PutObject (If-Match).")
                formatted_etag = f'"{clean_etag}"'

                try:
                    response = self._client.put_object(**put_kwargs, IfMatch=formatted_etag)
                except ClientError as exc:
                    err_code = str(exc.response.get("Error", {}).get("Code", ""))
                    if err_code in ("PreconditionFailed", "412", "AtLeastOneConditionFailed"):
                        logger.error("Conditional If-Match put_object rejected by S3: %s", exc)
                        raise S3ServiceError(
                            "Repository manifest concurrent modification detected (If-Match ETag mismatch). Overwrite rejected."
                        ) from exc
                    if err_code in ("InvalidArgument", "NotImplemented", "UnsupportedHeader"):
                        logger.error("S3 storage engine does not support conditional PutObject (If-Match): %s", exc)
                        raise S3ServiceError(
                            "S3 storage engine does not support conditional PutObject (If-Match). Manifest rotation rejected to prevent overwriting concurrent changes."
                        ) from exc
                    raise

            version_id = response.get("VersionId") if isinstance(response, dict) else None
            etag = response.get("ETag", "").strip('"') if isinstance(response, dict) else None
            return {
                "version_id": version_id,
                "etag": etag,
            }
        except ClientError as exc:
            logger.error("Failed to put repo manifest: %s", exc)
            raise S3ServiceError(f"Failed to put repo manifest: {exc}") from exc

    def get_repo_manifest_meta(self) -> dict[str, Any]:
        if not self._client or not self.bucket_name:
            raise S3ServiceError("S3 storage is not connected. Please configure and mount S3 via S3 Management.")
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=REPO_MANIFEST_KEY)
            raw = response["Body"].read()
            etag = response.get("ETag", "").strip('"') if isinstance(response, dict) else None
            version_id = response.get("VersionId") if isinstance(response, dict) else None
            return {
                "data": raw,
                "etag": etag,
                "version_id": version_id,
            }
        except ClientError as exc:
            logger.error("Failed to get repo manifest: %s", exc)
            raise S3ServiceError(f"Failed to get repo manifest: {exc}") from exc

    def get_repo_manifest(self) -> bytes:
        return self.get_repo_manifest_meta()["data"]
