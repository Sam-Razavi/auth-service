import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.token import RefreshToken
from app.utils.security import create_access_token, generate_raw_token, generate_token_hash


async def create_token_pair(user_id: uuid.UUID, db: AsyncSession) -> dict:
    settings = get_settings()
    raw_refresh = generate_raw_token()
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db.add(RefreshToken(
        user_id=user_id,
        token_hash=generate_token_hash(raw_refresh),
        expires_at=expires_at,
    ))
    await db.commit()

    return {
        "access_token": create_access_token(subject=str(user_id), jti=jti),
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


async def rotate_refresh_token(raw_token: str, db: AsyncSession) -> dict | None:
    token_hash = generate_token_hash(raw_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        return None

    stored.revoked = True
    await db.flush()

    return await create_token_pair(stored.user_id, db)


async def revoke_token(raw_token: str, db: AsyncSession) -> bool:
    token_hash = generate_token_hash(raw_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        return False
    stored.revoked = True
    await db.commit()
    return True


async def revoke_all_tokens(user_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    await db.commit()
    return result.rowcount
