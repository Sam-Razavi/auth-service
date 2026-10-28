from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models.user import User
from app.services.demo_service import ensure_demo_account
from app.utils.security import hash_password, verify_password

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo-pass-123"


@pytest.fixture
def demo_enabled(monkeypatch):
    monkeypatch.setenv("DEMO_ACCOUNT_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", DEMO_PASSWORD)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_demo_endpoint_is_404_without_a_demo_account(client):
    resp = await client.get("/auth/demo")
    assert resp.status_code == 404


async def test_demo_endpoint_returns_the_public_credentials(client, demo_enabled):
    resp = await client.get("/auth/demo")
    assert resp.status_code == 200
    assert resp.json() == {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}


async def test_ensure_creates_a_verified_regular_user(db, roles, demo_enabled):
    await ensure_demo_account(db)
    user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
    assert user.is_active and user.is_verified
    assert [r.name for r in user.roles] == ["user"]
    assert verify_password(DEMO_PASSWORD, user.hashed_password)


async def test_ensure_puts_a_tampered_account_back(db, roles, demo_enabled):
    db.add(
        User(
            email=DEMO_EMAIL,
            hashed_password=hash_password("someone-changed-it-1"),
            is_active=False,
            roles=[roles["admin"], roles["user"]],
        )
    )
    await db.commit()

    await ensure_demo_account(db)

    user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
    await db.refresh(user)
    assert user.is_active and user.is_verified
    assert [r.name for r in user.roles] == ["user"]  # never admin
    assert verify_password(DEMO_PASSWORD, user.hashed_password)


async def test_ensure_does_nothing_without_a_demo_account(db, roles):
    await ensure_demo_account(db)
    assert (await db.execute(select(User))).scalars().all() == []


async def test_demo_account_signs_in_and_is_not_an_admin(client, db, roles, demo_enabled):
    await ensure_demo_account(db)
    login = await client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert login.status_code == 200
    token = login.json()["access_token"]
    admin = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert admin.status_code == 403


async def test_demo_account_is_never_locked_out(client, db, roles, demo_enabled, mock_redis):
    await ensure_demo_account(db)
    mock_redis.incr = AsyncMock(return_value=6)  # past the lockout threshold
    resp = await client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200


async def test_other_accounts_are_still_locked_out(client, demo_enabled, mock_redis):
    await client.post("/auth/register", json={"email": "real@example.com", "password": "pass1234"})
    mock_redis.incr = AsyncMock(return_value=6)
    resp = await client.post("/auth/login", json={"email": "real@example.com", "password": "pass1234"})
    assert resp.status_code == 401


async def test_ensure_replaces_a_damaged_password_hash(db, roles, demo_enabled):
    db.add(User(email=DEMO_EMAIL, hashed_password="not-a-bcrypt-hash"))
    await db.commit()
    await ensure_demo_account(db)
    user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
    await db.refresh(user)
    assert verify_password(DEMO_PASSWORD, user.hashed_password)
