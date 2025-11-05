import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str


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
