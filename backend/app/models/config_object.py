from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConfigObject(Base):
    __tablename__ = "config_objects"
    __table_args__ = (
        CheckConstraint(
            "storage_status IN ('available', 'deleted', 'error', 'pending_delete')",
            name="ck_config_objects_storage_status",
        ),
        Index(
            "uq_config_object_content",
            "repository_id",
            "device_id",
            "content_sha256",
            unique=True,
        ),
        Index(
            "uq_config_object_s3_key",
            "repository_id",
            "s3_bucket",
            "s3_key",
            unique=True,
        ),
        Index("ix_config_objects_storage_status", "storage_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    object_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="available",
        server_default="available",
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    device = relationship("Device", back_populates="config_objects")
    snapshots = relationship("Snapshot", back_populates="config_object")
    storage_repository = relationship("StorageRepository", back_populates="config_objects")
