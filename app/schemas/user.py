import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*[\d\W]).{8,}$")


def _validate_password(value: str) -> str:
    if not _PASSWORD_RE.match(value):
        raise ValueError(
            "Password must be at least 8 characters and contain at least one letter "
            "and one number or special character."
        )
    return value


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password(v)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    roles: list[str] = []

    model_config = {"from_attributes": True}

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [r.name if hasattr(r, "name") else str(r) for r in v]
        return v
