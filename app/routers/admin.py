import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.rbac import require_role
from app.schemas.role import AssignRolesRequest
from app.schemas.user import UserResponse
from app.services.admin_service import (
    assign_roles_to_user,
    deactivate_user,
    get_user_by_id,
    list_users,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await list_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: uuid.UUID,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await assign_roles_to_user(user_id, data.roles, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await deactivate_user(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
