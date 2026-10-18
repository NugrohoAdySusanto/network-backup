from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import normalize_username


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    email: str | None = None
    password: str = Field(min_length=1, max_length=128)
    role: str

    @field_validator("username")
    @classmethod
    def normalize_username_field(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "visitor":
            normalized = "viewer"
        if normalized not in {"admin", "viewer"}:
            raise ValueError("INVALID_ROLE")
        return normalized
