import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User


async def list_users(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[User]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def assign_roles_to_user(
    user_id: uuid.UUID, role_names: list[str], db: AsyncSession
) -> User:
    user = await get_user_by_id(user_id, db)
    if not user:
        raise ValueError("User not found")

    result = await db.execute(select(Role).where(Role.name.in_(role_names)))
    roles = list(result.scalars().all())

    unknown = set(role_names) - {r.name for r in roles}
    if unknown:
        raise ValueError(f"Unknown roles: {', '.join(sorted(unknown))}")

    user.roles = roles
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    user = await get_user_by_id(user_id, db)
    if not user:
        return None
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
