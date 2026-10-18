from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StorageRepository(Base):
    __tablename__ = "storage_repositories"
    __table_args__ = (
        Index(
            "uq_storage_repositories_single_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    access_key: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    secure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    master_key_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repo_manifest: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(
        "Snapshot",
        back_populates="storage_repository",
    )
    config_objects: Mapped[list["ConfigObject"]] = relationship(
        "ConfigObject",
        back_populates="storage_repository",
    )
