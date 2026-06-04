from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.oauth import OAuthAccount
from app.models.user import User

settings = get_settings()

# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def get_github_auth_url(state: str) -> str:
    params = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
        "state": state,
    })
    return f"https://github.com/login/oauth/authorize?{params}"


async def exchange_github_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_github_email(access_token: str) -> str | None:
    """Fetch the primary verified email for users whose profile email is private."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        emails = resp.json()
    primary = next(
        (e["email"] for e in emails if e.get("primary") and e.get("verified")), None
    )
    return primary or next((e["email"] for e in emails if e.get("email")), None)


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

def get_google_auth_url(state: str) -> str:
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "state": state,
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


async def exchange_google_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_google_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Shared user upsert
# ---------------------------------------------------------------------------

async def upsert_oauth_user(
    provider: str,
    provider_user_id: str,
    provider_email: str | None,
    db: AsyncSession,
) -> User:
    """Find or create a User for an OAuth login, linking the provider account.

    Lookup order:
    1. Existing OAuthAccount → return its user (already linked).
    2. Existing User with matching email → link new OAuthAccount to it.
    3. No match → create User + OAuthAccount together.
    """
    result = await db.execute(
        select(OAuthAccount)
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
        .options(selectinload(OAuthAccount.user))
    )
    oauth_account = result.scalar_one_or_none()
    if oauth_account:
        return oauth_account.user

    user: User | None = None
    if provider_email:
        result = await db.execute(select(User).where(User.email == provider_email))
        user = result.scalar_one_or_none()

    if not user:
        if not provider_email:
            raise ValueError(
                f"Cannot create account: {provider} did not supply an email address"
            )
        user = User(email=provider_email, is_verified=True)
        db.add(user)
        await db.flush()

    db.add(OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
    ))
    await db.commit()
    await db.refresh(user)
    return user
