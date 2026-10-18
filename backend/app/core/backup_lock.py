
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from redis import Redis

from app.config import settings


_redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


@contextmanager
def device_backup_lock(device_id: int, job_id: Any = None) -> Iterator[bool]:
    lock = _redis.lock(
        f"backup-lock:device:{device_id}",
        timeout=settings.backup_lock_ttl_seconds,
        blocking_timeout=0,
    )
    acquired = bool(lock.acquire(blocking=False))
    hb_ctx = None
    if acquired and job_id is not None:
        hb_ctx = active_job_heartbeat(job_id=job_id, device_id=device_id)
        hb_ctx.__enter__()
    try:
        yield acquired
    finally:
        if hb_ctx is not None:
            hb_ctx.__exit__(None, None, None)
        if acquired:
            try:
                lock.release()
            except Exception:
                # Lock TTL is the final safety net.
                pass


def record_job_heartbeat(job_id: Any, ttl_seconds: int = 300) -> None:
    """Sets a heartbeat lease in Redis indicating the worker is actively running this job."""
    try:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        _redis.set(f"backup-heartbeat:job:{job_id}", now_iso, ex=ttl_seconds)
    except Exception:
        pass


def has_job_lease(job_id: Any) -> bool:
    """Checks whether an active heartbeat lease exists for the job."""
    try:
        return bool(_redis.exists(f"backup-heartbeat:job:{job_id}"))
    except Exception:
        return False


def extend_device_backup_lock(device_id: int, ttl_seconds: int | None = None) -> bool:
    """Extends the Redis TTL on the device backup lock while actively running."""
    try:
        ttl = ttl_seconds or settings.backup_lock_ttl_seconds
        return bool(_redis.expire(f"backup-lock:device:{device_id}", ttl))
    except Exception:
        return False


def clear_job_heartbeat(job_id: Any) -> None:
    """Removes the heartbeat lease when the job finishes or fails."""
    try:
        _redis.delete(f"backup-heartbeat:job:{job_id}")
    except Exception:
        pass


@contextmanager
def active_job_heartbeat(
    job_id: Any,
    device_id: int | None = None,
    interval_seconds: int = 15,
    ttl_seconds: int = 300,
) -> Iterator[None]:
    """
    Spawns a background renewal thread that periodically refreshes:
    1. The job heartbeat lease in Redis (TTL: ttl_seconds)
    2. The device backup lock in Redis (TTL: backup_lock_ttl_seconds)
    Terminates cleanly when the context manager exits, ensuring locks and leases
    never expire on long-running backup operations.
    """
    import logging
    import threading

    log = logging.getLogger(__name__)
    stop_event = threading.Event()

    # Record initial heartbeat immediately
    record_job_heartbeat(job_id, ttl_seconds=ttl_seconds)
    if device_id is not None:
        extend_device_backup_lock(device_id)

    def _renew_loop() -> None:
        while not stop_event.wait(timeout=interval_seconds):
            try:
                record_job_heartbeat(job_id, ttl_seconds=ttl_seconds)
                if device_id is not None:
                    extend_device_backup_lock(device_id)
            except Exception as exc:
                log.debug("Error in active_job_heartbeat renewal loop: %s", exc)

    thread = threading.Thread(
        target=_renew_loop,
        name=f"job-heartbeat-{job_id}",
        daemon=True,
    )
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=1.0)
        clear_job_heartbeat(job_id)


