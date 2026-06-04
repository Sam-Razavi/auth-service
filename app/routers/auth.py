import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.token import LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import authenticate_user, register_user
from app.services.token_service import (
    create_token_pair,
    revoke_all_tokens,
    revoke_token,
    rotate_refresh_token,
)
from app.utils.redis import blacklist_token, is_blacklisted
from app.utils.security import decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return user


@router.post("/login", response_model=TokenPair)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(data.email, data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return await create_token_pair(user.id, db)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await rotate_refresh_token(data.refresh_token, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await revoke_token(data.refresh_token, db)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not user_id or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    if await is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token already revoked")

    remaining = int(exp - datetime.now(timezone.utc).timestamp())
    if remaining > 0:
        await blacklist_token(jti, remaining)

    await revoke_all_tokens(uuid.UUID(user_id), db)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/verify-email/{token}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def verify_email(token: str):
    raise HTTPException(status_code=501, detail="Not implemented — Phase 4")


@router.post("/forgot-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def forgot_password():
    raise HTTPException(status_code=501, detail="Not implemented — Phase 4")


@router.post("/reset-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def reset_password():
    raise HTTPException(status_code=501, detail="Not implemented — Phase 4")
