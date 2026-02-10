"""
Tests for POST /auth/set-password — lets OAuth-only users add a local password.
"""
from unittest.mock import AsyncMock, patch


async def _oauth_login(client, email="oauth@example.com"):
    """Simulate an OAuth user by patching the GitHub callback to create a passwordless account."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_user,
        patch("app.routers.oauth.get_github_email", new_callable=AsyncMock) as mock_email_fn,
    ):
        mock_exchange.return_value = {"access_token": "tok"}
        mock_user.return_value = {"id": "9001", "login": "oauthuser", "email": email}
        mock_email_fn.return_value = None

        resp = await client.get("/oauth/github/callback?code=abc&state=s1")
        return resp.json()["access_token"]


async def test_set_password_for_oauth_user(client, mock_redis):
    mock_redis.delete = AsyncMock(return_value=1)  # OAuth state valid
    token = await _oauth_login(client)

    resp = await client.post(
        "/auth/set-password",
        json={"new_password": "myNewPass1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Can now log in with the password
    login = await client.post(
        "/auth/login", json={"email": "oauth@example.com", "password": "myNewPass1"}
    )
    assert login.status_code == 200


async def test_set_password_rejected_for_existing_password_user(client):
    await client.post("/auth/register", json={"email": "pw@example.com", "password": "pass1234"})
    login = await client.post("/auth/login", json={"email": "pw@example.com", "password": "pass1234"})
    token = login.json()["access_token"]

    resp = await client.post(
        "/auth/set-password",
        json={"new_password": "anotherpass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


async def test_set_password_requires_auth(client):
    resp = await client.post("/auth/set-password", json={"new_password": "myNewPass1"})
    assert resp.status_code == 403
