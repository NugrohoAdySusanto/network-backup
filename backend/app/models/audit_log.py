from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_category", "category"),
        Index("ix_audit_logs_severity", "severity"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_source_ip", "source_ip"),
        Index("ix_audit_logs_filter", "created_at", "category", "severity"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default="{}",
    )

    user = relationship("User", foreign_keys=[user_id])
