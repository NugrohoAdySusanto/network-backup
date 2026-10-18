from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.config_object import ConfigObject
from app.models.retention_mark import SnapshotRetentionMark
from app.models.snapshot import Snapshot
from app.services.s3_service import S3Service

logger = logging.getLogger(__name__)


class RetentionService:
    def __init__(self, db: Session, s3_service: S3Service | None = None) -> None:
        self.db = db
        self.s3_service = s3_service

    def _get_repo_s3_service(self, repo_id: Any) -> S3Service:
        if self.s3_service is not None:
            return self.s3_service
        try:
            return S3Service(repo_id=repo_id)
        except Exception as exc:
            logger.warning("Could not instantiate S3Service for repository %s: %s", repo_id, exc)
            return S3Service()

    def run_retention_policy(self, dry_run: bool = False, grace_period_seconds: int | None = None) -> dict[str, Any]:
        """
        Executes backup retention policies per storage repository (REL-02):
        Two-phase deletion:
        - Phase 1: Mark expired snapshots is_retained=False and stage unreferenced ConfigObjects
          with storage_status='pending_delete' and deleted_at timestamp. Commit DB transaction BEFORE touching S3.
        - Phase 2: Idempotently delete staged objects from S3 (respecting grace_period_seconds),
          then update storage_status to 'deleted' and commit DB.
        """
        now = datetime.now(timezone.utc)
        actual_grace_period = grace_period_seconds if grace_period_seconds is not None else settings.retention_purge_grace_hours * 3600
        logger.info("Starting per-repository two-phase retention policy run (dry_run=%s) at %s", dry_run, now.isoformat())

        # 1. Distinct repositories with active retained snapshots OR staged/pending_delete ConfigObjects
        repo_ids_stmt = (
            select(Snapshot.repository_id)
            .where(Snapshot.is_retained == True)  # noqa: E712
            .union(
                select(ConfigObject.repository_id)
                .where(
                    ConfigObject.storage_status.in_(["pending_delete", "available"]),
                    ConfigObject.deleted_at.is_not(None),
                )
            )
        )
        repo_ids = list(self.db.scalars(repo_ids_stmt).all())

        # Handle legacy or mock runs with no snapshots or unassigned repo_id
        if not repo_ids:
            dev_check = list(self.db.scalars(select(Snapshot.device_id).where(Snapshot.is_retained == True).distinct()).all())
            staged_check = list(self.db.scalars(select(ConfigObject.id).where(ConfigObject.deleted_at.is_not(None)).distinct()).all())
            if dev_check or staged_check:
                repo_ids = [None]

        total_retained = 0
        total_expired = 0
        objects_deleted = 0
        devices_processed: set[int] = set()

        for repo_id in repo_ids:
            repo_s3 = self._get_repo_s3_service(repo_id)
            repo_filter = (Snapshot.repository_id == repo_id) if repo_id is not None else Snapshot.repository_id.is_(None)

            # Find all devices with active retained snapshots in THIS repository
            device_ids_stmt = (
                select(Snapshot.device_id)
                .where(
                    Snapshot.is_retained == True,  # noqa: E712
                    repo_filter,
                )
                .distinct()
            )
            device_ids = list(self.db.scalars(device_ids_stmt).all())
            devices_processed.update(device_ids)

            repo_expired_snapshot_ids: list[int] = []
            for device_id in device_ids:
                retained, expired, exp_ids = self._evaluate_device_repo_retention(
                    device_id=device_id,
                    repository_id=repo_id,
                    now=now,
                    dry_run=dry_run,
                )
                total_retained += retained
                total_expired += expired
                repo_expired_snapshot_ids.extend(exp_ids)

            if not dry_run:
                if repo_expired_snapshot_ids:
                    # --- PHASE 1: Stage unreferenced objects in DB and commit ---
                    self._stage_repo_unreferenced_objects(
                        repository_id=repo_id,
                        now=now,
                    )
                    self.db.commit()
                    logger.info("Phase 1 committed: snapshots expired and unreferenced objects staged (repo: %s)", repo_id)
                else:
                    self.db.commit()

                # --- PHASE 2: Idempotent physical deletion from S3 and commit ---
                # Runs unconditionally on every non-dry-run pass to recover any pending deletions from crashes
                deleted_in_repo = self._purge_repo_staged_objects(
                    repository_id=repo_id,
                    repo_s3=repo_s3,
                    now=now,
                    grace_period_seconds=actual_grace_period,
                )
                objects_deleted += deleted_in_repo
            elif not dry_run:
                self.db.commit()

        summary = {
            "status": "success",
            "dry_run": dry_run,
            "devices_processed": len(devices_processed),
            "snapshots_retained": total_retained,
            "snapshots_expired": total_expired,
            "objects_deleted": objects_deleted,
            "executed_at": now.isoformat(),
        }
        logger.info("Retention policy completed: %s", summary)
        return summary

    def _evaluate_device_repo_retention(
        self,
        *,
        device_id: int,
        repository_id: Any,
        now: datetime,
        dry_run: bool,
    ) -> tuple[int, int, list[int]]:
        """
        Evaluates retention for snapshots of a single device within a specific repository.
        Guarantees that the newest successful snapshot for this device in this repository is never expired.
        """
        repo_filter = (Snapshot.repository_id == repository_id) if repository_id is not None else Snapshot.repository_id.is_(None)
        snapshots = list(
            self.db.scalars(
                select(Snapshot)
                .where(
                    Snapshot.device_id == device_id,
                    Snapshot.is_retained == True,  # noqa: E712
                    repo_filter,
                )
                .order_by(Snapshot.captured_at.desc())
            ).all()
        )

        if not snapshots:
            return 0, 0, []

        retained_snapshots: set[int] = set()
        expired_snapshot_ids: list[int] = []
        marks_to_add: list[SnapshotRetentionMark] = []

        # 1. Latest-Known-Good Guard per (device, repository): The newest snapshot MUST ALWAYS be retained
        latest_good = snapshots[0]
        retained_snapshots.add(latest_good.id)
        marks_to_add.append(
            SnapshotRetentionMark(
                snapshot_id=latest_good.id,
                mark_type="LATEST_GOOD",
                marked_at=now,
            )
        )

        cutoff_31 = now - timedelta(days=31)
        cutoff_7_days = now - timedelta(days=7)
        cutoff_4_weeks = now - timedelta(weeks=4)
        cutoff_12_months = now - timedelta(days=365)
        cutoff_3_years = now - timedelta(days=365 * 3)

        # Tracking sets for GFS tiers to pick the latest snapshot per bucket
        seen_days: set[str] = set()
        seen_weeks: set[str] = set()
        seen_months: set[str] = set()
        seen_years: set[str] = set()

        for snap in snapshots:
            snap_time = snap.captured_at
            policy = snap.retention_policy_at_capture or "standard_31"
            keep = snap.id == latest_good.id

            if policy == "standard_31":
                if snap_time >= cutoff_31:
                    keep = True
                    marks_to_add.append(
                        SnapshotRetentionMark(
                            snapshot_id=snap.id,
                            mark_type="STANDARD_WINDOW",
                            marked_at=now,
                        )
                    )

            elif policy == "smart_7_4_12_3":
                day_key = snap_time.strftime("%Y-%m-%d")
                week_key = f"{snap_time.isocalendar()[0]}-W{snap_time.isocalendar()[1]:02d}"
                month_key = snap_time.strftime("%Y-%m")
                year_key = snap_time.strftime("%Y")

                # Daily tier: 7 days
                if snap_time >= cutoff_7_days and len(seen_days) < 7 and day_key not in seen_days:
                    seen_days.add(day_key)
                    keep = True
                    marks_to_add.append(
                        SnapshotRetentionMark(
                            snapshot_id=snap.id,
                            mark_type="DAILY",
                            marked_at=now,
                        )
                    )

                # Weekly tier: 4 weeks
                if snap_time >= cutoff_4_weeks and len(seen_weeks) < 4 and week_key not in seen_weeks:
                    seen_weeks.add(week_key)
                    keep = True
                    marks_to_add.append(
                        SnapshotRetentionMark(
                            snapshot_id=snap.id,
                            mark_type="WEEKLY",
                            marked_at=now,
                        )
                    )

                # Monthly tier: 12 months
                if snap_time >= cutoff_12_months and len(seen_months) < 12 and month_key not in seen_months:
                    seen_months.add(month_key)
                    keep = True
                    marks_to_add.append(
                        SnapshotRetentionMark(
                            snapshot_id=snap.id,
                            mark_type="MONTHLY",
                            marked_at=now,
                        )
                    )

                # Yearly tier: 3 years
                if snap_time >= cutoff_3_years and len(seen_years) < 3 and year_key not in seen_years:
                    seen_years.add(year_key)
                    keep = True
                    marks_to_add.append(
                        SnapshotRetentionMark(
                            snapshot_id=snap.id,
                            mark_type="YEARLY",
                            marked_at=now,
                        )
                    )

            if keep:
                retained_snapshots.add(snap.id)
            else:
                expired_snapshot_ids.append(snap.id)
                if not dry_run:
                    snap.is_retained = False
                    snap.expired_at = now

        if not dry_run:
            # Synchronize retention marks: clear obsolete marks for evaluated snapshots
            snap_ids = [s.id for s in snapshots]
            if snap_ids:
                self.db.query(SnapshotRetentionMark).filter(
                    SnapshotRetentionMark.snapshot_id.in_(snap_ids)
                ).delete(synchronize_session=False)

            for mark in marks_to_add:
                try:
                    self.db.add(mark)
                except Exception as exc:
                    logger.debug("Could not add retention mark: %s", exc)

        return len(retained_snapshots), len(expired_snapshot_ids), expired_snapshot_ids

    def _evaluate_device_retention(
        self,
        *,
        device_id: int,
        now: datetime,
        dry_run: bool,
    ) -> tuple[int, int, list[int]]:
        """Backwards compatibility helper."""
        return self._evaluate_device_repo_retention(
            device_id=device_id,
            repository_id=None,
            now=now,
            dry_run=dry_run,
        )

    def _stage_repo_unreferenced_objects(
        self,
        *,
        repository_id: Any,
        now: datetime,
    ) -> int:
        """
        Phase 1: Identifies ConfigObjects in repository with 0 active snapshots,
        and marks them with storage_status='pending_delete' and deleted_at = now.
        Does NOT touch S3. DB is committed in caller before Phase 2.
        """
        repo_snap_filter = (Snapshot.repository_id == repository_id) if repository_id is not None else Snapshot.repository_id.is_(None)
        repo_obj_filter = (ConfigObject.repository_id == repository_id) if repository_id is not None else ConfigObject.repository_id.is_(None)

        active_config_ids = (
            select(Snapshot.config_object_id)
            .where(
                Snapshot.is_retained == True,  # noqa: E712
                repo_snap_filter,
            )
            .distinct()
        )

        orphans = list(
            self.db.scalars(
                select(ConfigObject).where(
                    ConfigObject.storage_status == "available",
                    ConfigObject.deleted_at.is_(None),
                    repo_obj_filter,
                    ConfigObject.id.not_in(active_config_ids),
                )
            ).all()
        )

        staged_count = 0
        for obj in orphans:
            obj.storage_status = "pending_delete"
            obj.deleted_at = now
            staged_count += 1
            logger.info("Staged unreferenced ConfigObject %s (%s) as pending_delete (repo: %s)", obj.id, obj.s3_key, repository_id)

        return staged_count

    def _purge_repo_staged_objects(
        self,
        *,
        repository_id: Any,
        repo_s3: S3Service,
        now: datetime,
        grace_period_seconds: int = 0,
    ) -> int:
        """
        Phase 2: Idempotently deletes staged ConfigObjects from S3 and marks them as 'deleted' in DB.
        Honors grace_period_seconds before physical S3 deletion.
        Performs atomic row-lock and anti-join verification against active retained snapshots before S3 deletion.
        """
        repo_obj_filter = (ConfigObject.repository_id == repository_id) if repository_id is not None else ConfigObject.repository_id.is_(None)

        grace_cutoff = now - timedelta(seconds=grace_period_seconds) if grace_period_seconds > 0 else now

        staged_ids = list(
            self.db.scalars(
                select(ConfigObject.id).where(
                    ConfigObject.storage_status.in_(["pending_delete", "available"]),
                    ConfigObject.deleted_at.is_not(None),
                    ConfigObject.deleted_at <= grace_cutoff,
                    repo_obj_filter,
                )
            ).all()
        )

        deleted_count = 0
        for obj_id in staged_ids:
            try:
                # Lock row during final deletion check
                locked_obj = self.db.scalar(
                    select(ConfigObject)
                    .where(ConfigObject.id == obj_id)
                    .with_for_update()
                )
                if not locked_obj:
                    continue

                # Anti-join / recheck: verify no active retained snapshot references this object!
                active_ref_count = self.db.scalar(
                    select(func.count(Snapshot.id)).where(
                        Snapshot.config_object_id == locked_obj.id,
                        Snapshot.is_retained == True,  # noqa: E712
                    )
                ) or 0

                if active_ref_count > 0:
                    logger.warning(
                        "ConfigObject %s (%s) is referenced by %d active retained snapshot(s); cancelling pending deletion and restoring to available",
                        locked_obj.id,
                        locked_obj.s3_key,
                        active_ref_count,
                    )
                    locked_obj.storage_status = "available"
                    locked_obj.deleted_at = None
                    self.db.commit()
                    continue

                # Idempotent S3 delete
                deleted = repo_s3.delete_object(
                    s3_key=locked_obj.s3_key,
                    bucket=locked_obj.s3_bucket,
                )
                if deleted:
                    locked_obj.storage_status = "deleted"
                    self.db.commit()
                    deleted_count += 1
                    logger.info("Purged staged ConfigObject %s (%s) from S3 (repo: %s)", locked_obj.id, locked_obj.s3_key, repository_id)
            except Exception as exc:
                self.db.rollback()
                logger.error("Failed to delete staged ConfigObject %s from S3: %s", obj_id, exc)

        return deleted_count

    def purge_pending_deleted_objects(
        self,
        repository_id: Any = None,
        grace_period_seconds: int | None = None,
    ) -> int:
        """Standalone task to perform Phase 2 physical deletion of staged objects for a specific repo."""
        actual_grace = grace_period_seconds if grace_period_seconds is not None else settings.retention_purge_grace_hours * 3600
        now = datetime.now(timezone.utc)
        repo_s3 = self._get_repo_s3_service(repository_id)
        return self._purge_repo_staged_objects(
            repository_id=repository_id,
            repo_s3=repo_s3,
            now=now,
            grace_period_seconds=actual_grace,
        )

    def purge_pending_deleted_objects_all_repos(
        self,
        grace_period_seconds: int | None = None,
    ) -> int:
        """Maintenance task: purges pending_delete objects across all repositories after grace period."""
        actual_grace = grace_period_seconds if grace_period_seconds is not None else settings.retention_purge_grace_hours * 3600
        now = datetime.now(timezone.utc)
        repo_ids = list(
            self.db.scalars(
                select(ConfigObject.repository_id)
                .where(
                    ConfigObject.storage_status.in_(["pending_delete", "available"]),
                    ConfigObject.deleted_at.is_not(None),
                )
                .distinct()
            ).all()
        )
        if not repo_ids:
            repo_ids = [None]

        total_purged = 0
        for repo_id in repo_ids:
            repo_s3 = self._get_repo_s3_service(repo_id)
            total_purged += self._purge_repo_staged_objects(
                repository_id=repo_id,
                repo_s3=repo_s3,
                now=now,
                grace_period_seconds=actual_grace,
            )
        return total_purged

    def _cleanup_repo_unreferenced_objects(
        self,
        *,
        repository_id: Any,
        repo_s3: S3Service,
        now: datetime,
    ) -> int:
        """Backwards compatibility helper: stages orphans, commits DB, then purges from S3."""
        self._stage_repo_unreferenced_objects(repository_id=repository_id, now=now)
        self.db.commit()
        return self._purge_repo_staged_objects(
            repository_id=repository_id,
            repo_s3=repo_s3,
            now=now,
            grace_period_seconds=0,
        )

    def _cleanup_unreferenced_objects(self, now: datetime) -> int:
        """Backwards compatibility helper."""
        s3 = self.s3_service or S3Service()
        return self._cleanup_repo_unreferenced_objects(
            repository_id=None,
            repo_s3=s3,
            now=now,
        )

