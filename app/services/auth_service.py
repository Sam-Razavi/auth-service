from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import hash_password, verify_password
import app.utils.redis as _redis_utils

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes


def _lockout_key(email: str) -> str:
    return f"login_attempts:{email}"


async def register_user(data: UserCreate, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User | None:
    r = await _redis_utils.get_redis()
    key = _lockout_key(email)
    attempts = await r.incr(key)
    if attempts == 1:
        await r.expire(key, _LOCKOUT_SECONDS)

    if attempts > _MAX_ATTEMPTS:
        return None  # locked — treat same as wrong credentials

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None

    # Success — clear the counter
    await r.delete(key)
    return user
