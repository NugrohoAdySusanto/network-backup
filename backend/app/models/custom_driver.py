from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomDriver(Base):
    __tablename__ = "custom_drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_hint: Mapped[str] = mapped_column(String(128), nullable=False)
    model_hint: Mapped[str] = mapped_column(String(128), nullable=False)
    transport: Mapped[str] = mapped_column(String(32), nullable=False, default="ssh")
    default_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    connect_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    command_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    
    # Privilege / Enable Mode
    need_enable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enable_command: Mapped[str] = mapped_column(String(64), nullable=False, default="enable")
    enable_prompt_pattern: Mapped[str] = mapped_column(String(64), nullable=False, default=r"[#$]")
    
    # Paging & Collection
    disable_paging_command: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paging_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    backup_command: Mapped[str] = mapped_column(String(255), nullable=False, default="show running-config")
    output_extension: Mapped[str] = mapped_column(String(16), nullable=False, default="txt")
    
    # Normalization & Validation
    strip_patterns: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=list)
    validation_min_length: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    validation_required_keyword: Mapped[str | None] = mapped_column(String(64), nullable=True, default="hostname")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
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
