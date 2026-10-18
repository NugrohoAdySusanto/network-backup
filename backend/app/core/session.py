from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from redis import Redis

from app.config import settings


@dataclass(frozen=True)
class SessionData:
    user_id: int
    csrf_token: str
    remember_me: bool
    created_at: str


class SessionStore:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _key(session_id: str) -> str:
        return f"web-session:{session_id}"

    @staticmethod
    def generate_session_id() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_csrf_token() -> str:
        return secrets.token_urlsafe(32)

    def create(self, *, user_id: int, remember_me: bool) -> tuple[str, SessionData, int]:
        session_id = self.generate_session_id()
        data = SessionData(
            user_id=user_id,
            csrf_token=self.generate_csrf_token(),
            remember_me=remember_me,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        ttl = (
            settings.remember_session_ttl_seconds
            if remember_me
            else settings.session_ttl_seconds
        )
        self._redis.setex(
            self._key(session_id),
            ttl,
            json.dumps(asdict(data)),
        )
        return session_id, data, ttl

    def get(self, session_id: str) -> SessionData | None:
        raw = self._redis.get(self._key(session_id))
        if raw is None:
            return None

        payload = json.loads(raw)
        return SessionData(
            user_id=int(payload["user_id"]),
            csrf_token=str(payload["csrf_token"]),
            remember_me=bool(payload["remember_me"]),
            created_at=str(payload["created_at"]),
        )

    def delete(self, session_id: str) -> None:
        self._redis.delete(self._key(session_id))

    def touch(self, session_id: str, remember_me: bool) -> None:
        ttl = (
            settings.remember_session_ttl_seconds
            if remember_me
            else settings.session_ttl_seconds
        )
        self._redis.expire(self._key(session_id), ttl)


def create_redis_client() -> Redis:
    return Redis.from_url(
        settings.session_redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )


session_store = SessionStore(create_redis_client())
