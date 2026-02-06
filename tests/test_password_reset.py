"""
Phase 4 — password reset and email verification tests.

Email sending is mocked globally via the mock_email_service fixture in conftest.
Tests retrieve raw tokens from mock call args (the raw token is the second
positional argument to both send_password_reset_email and send_verification_email).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.reset_token import PasswordResetToken
from app.models.user import User
from app.utils.security import generate_token_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register(client, email="u@example.com", password="pass1234"):
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()


async def _login_tokens(client, email, password="pass1234"):
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"], resp.json()["refresh_token"]


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

async def test_forgot_password_unknown_email_returns_200(client):
    resp = await client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 200


async def test_forgot_password_known_email_sends_reset_email(client, mock_email_service):
    await _register(client, "reset@example.com")
    mock_email_service["reset"].reset_mock()

    resp = await client.post("/auth/forgot-password", json={"email": "reset@example.com"})
    assert resp.status_code == 200
    assert mock_email_service["reset"].call_count == 1
    assert mock_email_service["reset"].call_args.args[0] == "reset@example.com"


async def test_forgot_password_inactive_user_no_email(client, db, mock_email_service):
    await _register(client, "inactive@example.com")
    result = await db.execute(select(User).where(User.email == "inactive@example.com"))
    user = result.scalar_one()
    user.is_active = False
    await db.commit()

    mock_email_service["reset"].reset_mock()
    resp = await client.post("/auth/forgot-password", json={"email": "inactive@example.com"})
    assert resp.status_code == 200
    mock_email_service["reset"].assert_not_called()


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

async def test_reset_password_success(client, mock_email_service):
    await _register(client, "resetok@example.com")
    mock_email_service["reset"].reset_mock()

    await client.post("/auth/forgot-password", json={"email": "resetok@example.com"})
    raw_token = mock_email_service["reset"].call_args.args[1]

    resp = await client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "brand_new_pass"},
    )
    assert resp.status_code == 200

    bad = await client.post(
        "/auth/login", json={"email": "resetok@example.com", "password": "pass1234"}
    )
    assert bad.status_code == 401

    good = await client.post(
        "/auth/login", json={"email": "resetok@example.com", "password": "brand_new_pass"}
    )
    assert good.status_code == 200


async def test_reset_password_invalid_token(client):
    resp = await client.post(
        "/auth/reset-password",
        json={"token": "completely_made_up_token", "new_password": "newpass123"},
    )
    assert resp.status_code == 400


async def test_reset_password_used_token(client, mock_email_service):
    await _register(client, "reused@example.com")
    mock_email_service["reset"].reset_mock()

    await client.post("/auth/forgot-password", json={"email": "reused@example.com"})
    raw_token = mock_email_service["reset"].call_args.args[1]

    await client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "first_new_pass"}
    )
    resp = await client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "second_new_pass"}
    )
    assert resp.status_code == 400


async def test_reset_password_expired_token(client, db, mock_email_service):
    await _register(client, "expired@example.com")
    result = await db.execute(select(User).where(User.email == "expired@example.com"))
    user = result.scalar_one()

    raw_token = "my_expired_test_token_hex"
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=generate_token_hash(raw_token),
        purpose="password_reset",
        expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=2),
    ))
    await db.commit()

    resp = await client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "newpass123"},
    )
    assert resp.status_code == 400


async def test_reset_password_revokes_existing_sessions(client, mock_email_service):
    await _register(client, "revoke@example.com")
    _, refresh_token = await _login_tokens(client, "revoke@example.com")

    mock_email_service["reset"].reset_mock()
    await client.post("/auth/forgot-password", json={"email": "revoke@example.com"})
    raw_token = mock_email_service["reset"].call_args.args[1]

    await client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "newpass999"},
    )

    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


async def test_reset_password_too_short_rejected(client, mock_email_service):
    await _register(client, "short@example.com")
    mock_email_service["reset"].reset_mock()

    await client.post("/auth/forgot-password", json={"email": "short@example.com"})
    raw_token = mock_email_service["reset"].call_args.args[1]

    resp = await client.post(
        "/auth/reset-password",
        json={"token": raw_token, "new_password": "short"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/verify-email/{token}
# ---------------------------------------------------------------------------

async def test_register_sends_verification_email(client, mock_email_service):
    await _register(client, "newuser@example.com")
    assert mock_email_service["verify"].call_count == 1
    assert mock_email_service["verify"].call_args.args[0] == "newuser@example.com"


async def test_verify_email_success(client, db, mock_email_service):
    await _register(client, "verify@example.com")
    raw_token = mock_email_service["verify"].call_args.args[1]

    result = await db.execute(select(User).where(User.email == "verify@example.com"))
    user = result.scalar_one()
    assert user.is_verified is False

    resp = await client.post(f"/auth/verify-email/{raw_token}")
    assert resp.status_code == 200

    await db.refresh(user)
    assert user.is_verified is True


async def test_verify_email_invalid_token(client):
    resp = await client.post("/auth/verify-email/not_a_real_token")
    assert resp.status_code == 400


async def test_verify_email_used_token(client, mock_email_service):
    await _register(client, "verifytwice@example.com")
    raw_token = mock_email_service["verify"].call_args.args[1]

    await client.post(f"/auth/verify-email/{raw_token}")
    resp = await client.post(f"/auth/verify-email/{raw_token}")
    assert resp.status_code == 400


async def test_verify_email_expired_token(client, db, mock_email_service):
    await _register(client, "expiredverify@example.com")
    result = await db.execute(select(User).where(User.email == "expiredverify@example.com"))
    user = result.scalar_one()

    raw_token = "expired_verify_token_hex"
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=generate_token_hash(raw_token),
        purpose="email_verification",
        expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
    ))
    await db.commit()

    resp = await client.post(f"/auth/verify-email/{raw_token}")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /auth/verify-email/resend
# ---------------------------------------------------------------------------

async def test_resend_verification_unknown_email_returns_200(client):
    resp = await client.post("/auth/verify-email/resend", json={"email": "ghost@example.com"})
    assert resp.status_code == 200


async def test_resend_verification_sends_new_email(client, mock_email_service):
    await _register(client, "resend@example.com")
    mock_email_service["verify"].reset_mock()

    resp = await client.post("/auth/verify-email/resend", json={"email": "resend@example.com"})
    assert resp.status_code == 200
    assert mock_email_service["verify"].call_count == 1


async def test_resend_already_verified_no_email(client, mock_email_service):
    await _register(client, "alreadyverified@example.com")
    raw_token = mock_email_service["verify"].call_args.args[1]
    await client.post(f"/auth/verify-email/{raw_token}")

    mock_email_service["verify"].reset_mock()
    resp = await client.post("/auth/verify-email/resend", json={"email": "alreadyverified@example.com"})
    assert resp.status_code == 200
    mock_email_service["verify"].assert_not_called()
