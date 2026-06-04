from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class SetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
