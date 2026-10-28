"""The public demo account: a normal user whose password is published on purpose.

Off unless DEMO_ACCOUNT_EMAIL and DEMO_ACCOUNT_PASSWORD are set. When they are, the
account is created (or put back in shape) on startup, the web UI offers it as a
one-click sign-in, and it's exempt from the failed-login lockout, so nobody can lock
visitors out by guessing wrong on purpose (the per-IP rate limit still applies).

It only ever has the `user` role, so a visitor can't reach the admin endpoints. Use an
address that can't receive mail (e.g. @example.com), so reset and verification emails
for it go nowhere.
"""
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.role import Role
from app.models.user import User
from app.utils.security import hash_password, verify_password

log = structlog.get_logger()


def demo_credentials() -> tuple[str, str] | None:
    settings = get_settings()
    if settings.DEMO_ACCOUNT_EMAIL and settings.DEMO_ACCOUNT_PASSWORD:
        return settings.DEMO_ACCOUNT_EMAIL.lower(), settings.DEMO_ACCOUNT_PASSWORD
    return None


def is_demo_email(email: str) -> bool:
    creds = demo_credentials()
    return creds is not None and email.lower() == creds[0]


def _password_matches(password: str, hashed: str | None) -> bool:
    # A damaged hash (not valid bcrypt) raises instead of failing to match; either way
    # the reset below has to replace it, so treat it as a mismatch.
    try:
        return bool(hashed) and verify_password(password, hashed)
    except ValueError:
        return False


async def ensure_demo_account(db: AsyncSession) -> None:
    """Creates the demo user, or resets it to a known state: active, verified, the
    configured password, and the `user` role only. Safe to run on every start."""
    creds = demo_credentials()
    if creds is None:
        return
    email, password = creds

    user_role = (await db.execute(select(Role).where(Role.name == "user"))).scalar_one_or_none()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, hashed_password=hash_password(password))
        db.add(user)
        outcome = "created"
    else:
        if not _password_matches(password, user.hashed_password):
            user.hashed_password = hash_password(password)
        outcome = "reset"
    user.is_active = True
    user.is_verified = True
    user.roles = [user_role] if user_role else []
    await db.commit()
    log.info("demo_account", outcome=outcome, email=email)
