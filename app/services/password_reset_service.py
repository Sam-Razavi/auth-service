import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reset_token import PasswordResetToken
from app.models.user import User
from app.services import email_service
from app.services.token_service import revoke_all_tokens
from app.utils.security import generate_raw_token, generate_token_hash, hash_password

_RESET_EXPIRE_HOURS = 1
_VERIFY_EXPIRE_HOURS = 24


async def request_password_reset(email: str, db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return  # never reveal whether the address exists

    raw_token = generate_raw_token()
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=generate_token_hash(raw_token),
        purpose="password_reset",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=_RESET_EXPIRE_HOURS),
    ))
    await db.commit()
    await email_service.send_password_reset_email(user.email, raw_token)


async def consume_reset_token(raw_token: str, new_password: str, db: AsyncSession) -> bool:
    record = await _fetch_valid_token(raw_token, "password_reset", db)
    if record is None:
        return False

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return False

    record.used_at = datetime.now(tz=timezone.utc)
    user.hashed_password = hash_password(new_password)
    await db.commit()
    await revoke_all_tokens(user.id, db)
    return True


async def send_verification_token(user_id: uuid.UUID, email: str, db: AsyncSession) -> None:
    raw_token = generate_raw_token()
    db.add(PasswordResetToken(
        user_id=user_id,
        token_hash=generate_token_hash(raw_token),
        purpose="email_verification",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=_VERIFY_EXPIRE_HOURS),
    ))
    await db.commit()
    await email_service.send_verification_email(email, raw_token)


async def resend_verification_token(email: str, db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.is_verified:
        return  # silently no-op: don't leak info or resend unnecessarily
    await send_verification_token(user.id, user.email, db)


async def consume_verification_token(raw_token: str, db: AsyncSession) -> bool:
    record = await _fetch_valid_token(raw_token, "email_verification", db)
    if record is None:
        return False

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    record.used_at = datetime.now(tz=timezone.utc)
    user.is_verified = True
    await db.commit()
    return True


async def _fetch_valid_token(
    raw_token: str, purpose: str, db: AsyncSession
) -> PasswordResetToken | None:
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == generate_token_hash(raw_token),
            PasswordResetToken.purpose == purpose,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    if record.used_at is not None:
        return None
    # SQLite stores datetimes without timezone; normalise to UTC-aware before comparing
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(tz=timezone.utc):
        return None
    return record
