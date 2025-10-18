import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.token import TokenPair
from app.services.oauth_service import (
    exchange_github_code,
    exchange_google_code,
    get_github_auth_url,
    get_github_email,
    get_github_user,
    get_google_auth_url,
    get_google_user,
    upsert_oauth_user,
)
from app.services.token_service import create_token_pair
from app.utils.redis import store_oauth_state, verify_and_consume_oauth_state

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/github", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def github_login():
    state = secrets.token_urlsafe(32)
    await store_oauth_state(state)
    return RedirectResponse(get_github_auth_url(state), status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/github/callback", response_model=TokenPair)
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if not await verify_and_consume_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    token_data = await exchange_github_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token exchange failed",
        )

    profile = await get_github_user(access_token)
    email = profile.get("email") or await get_github_email(access_token)

    try:
        user = await upsert_oauth_user(
            provider="github",
            provider_user_id=str(profile["id"]),
            provider_email=email,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return await create_token_pair(user.id, db)


@router.get("/google", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def google_login():
    state = secrets.token_urlsafe(32)
    await store_oauth_state(state)
    return RedirectResponse(get_google_auth_url(state), status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback", response_model=TokenPair)
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if not await verify_and_consume_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    token_data = await exchange_google_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange failed",
        )

    profile = await get_google_user(access_token)
    email = profile.get("email")

    try:
        user = await upsert_oauth_user(
            provider="google",
            provider_user_id=str(profile["sub"]),
            provider_email=email,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return await create_token_pair(user.id, db)
