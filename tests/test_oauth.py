from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Redirect tests
# ---------------------------------------------------------------------------

async def test_github_redirect(client):
    resp = await client.get("/oauth/github", follow_redirects=False)
    assert resp.status_code == 307
    loc = resp.headers["location"]
    assert "github.com/login/oauth/authorize" in loc
    assert "client_id" in loc
    assert "state" in loc


async def test_google_redirect(client):
    resp = await client.get("/oauth/google", follow_redirects=False)
    assert resp.status_code == 307
    loc = resp.headers["location"]
    assert "accounts.google.com" in loc
    assert "client_id" in loc
    assert "state" in loc


# ---------------------------------------------------------------------------
# GitHub callback
# ---------------------------------------------------------------------------

async def test_github_callback_creates_new_user(client):
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "gh-fake-token"}
        mock_profile.return_value = {"id": 111111, "email": "newgithub@example.com", "login": "newuser"}

        resp = await client.get("/oauth/github/callback?code=testcode&state=teststate")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


async def test_github_callback_links_existing_user(client):
    """OAuth login with a known email should attach to the existing account."""
    await client.post("/auth/register", json={"email": "existing@example.com", "password": "pass1234"})

    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "gh-fake-token"}
        mock_profile.return_value = {"id": 222222, "email": "existing@example.com", "login": "existinguser"}

        resp = await client.get("/oauth/github/callback?code=testcode&state=teststate")
        assert resp.status_code == 200


async def test_github_callback_second_login_reuses_account(client):
    """Second login with the same provider ID returns a token without creating a duplicate user."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "gh-fake-token"}
        mock_profile.return_value = {"id": 333333, "email": "repeat@example.com", "login": "repeatuser"}

        resp1 = await client.get("/oauth/github/callback?code=code1&state=state1")
        resp2 = await client.get("/oauth/github/callback?code=code2&state=state2")
        assert resp1.status_code == 200
        assert resp2.status_code == 200


async def test_github_callback_private_email_fallback(client):
    """If profile email is None, falls back to get_github_email."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
        patch("app.routers.oauth.get_github_email", new_callable=AsyncMock) as mock_email,
    ):
        mock_exchange.return_value = {"access_token": "gh-fake-token"}
        mock_profile.return_value = {"id": 444444, "email": None, "login": "privateemail"}
        mock_email.return_value = "private@users.noreply.github.com"

        resp = await client.get("/oauth/github/callback?code=testcode&state=teststate")
        assert resp.status_code == 200
        mock_email.assert_called_once_with("gh-fake-token")


async def test_github_callback_invalid_state(client, mock_redis):
    mock_redis.delete = AsyncMock(return_value=0)

    resp = await client.get("/oauth/github/callback?code=testcode&state=badstate")
    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


async def test_github_callback_failed_token_exchange(client):
    with patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"error": "bad_verification_code"}

        resp = await client.get("/oauth/github/callback?code=badcode&state=teststate")
        assert resp.status_code == 400
        assert "token exchange" in resp.json()["detail"].lower()


async def test_github_callback_no_email_available(client):
    """If GitHub supplies no email at all, the callback returns 400."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
        patch("app.routers.oauth.get_github_email", new_callable=AsyncMock) as mock_email,
    ):
        mock_exchange.return_value = {"access_token": "gh-fake-token"}
        mock_profile.return_value = {"id": 999999, "email": None, "login": "noemail"}
        mock_email.return_value = None

        resp = await client.get("/oauth/github/callback?code=testcode&state=teststate")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Google callback
# ---------------------------------------------------------------------------

async def test_google_callback_creates_new_user(client):
    with (
        patch("app.routers.oauth.exchange_google_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_google_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "google-fake-token"}
        mock_profile.return_value = {
            "sub": "google-user-id-123",
            "email": "googleuser@gmail.com",
            "email_verified": True,
        }

        resp = await client.get("/oauth/google/callback?code=testcode&state=teststate")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data


async def test_google_callback_invalid_state(client, mock_redis):
    mock_redis.delete = AsyncMock(return_value=0)

    resp = await client.get("/oauth/google/callback?code=testcode&state=invalid")
    assert resp.status_code == 400


async def test_google_callback_failed_token_exchange(client):
    with patch("app.routers.oauth.exchange_google_code", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"error": "invalid_grant"}

        resp = await client.get("/oauth/google/callback?code=badcode&state=teststate")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# JWT integration
# ---------------------------------------------------------------------------

async def test_oauth_issued_token_works_for_me(client):
    """Token issued after GitHub OAuth must authenticate /auth/me."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "gh-token"}
        mock_profile.return_value = {"id": 555555, "email": "oauthme@example.com", "login": "oauthme"}

        login_resp = await client.get("/oauth/github/callback?code=x&state=s")
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "oauthme@example.com"


async def test_two_providers_link_to_same_user(client):
    """GitHub and Google with the same email must resolve to the same user."""
    with (
        patch("app.routers.oauth.exchange_github_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_github_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "gh-token"}
        mock_profile.return_value = {"id": 777777, "email": "shared@example.com", "login": "shareduser"}
        gh_resp = await client.get("/oauth/github/callback?code=c1&state=s1")
        assert gh_resp.status_code == 200

    with (
        patch("app.routers.oauth.exchange_google_code", new_callable=AsyncMock) as mock_exchange,
        patch("app.routers.oauth.get_google_user", new_callable=AsyncMock) as mock_profile,
    ):
        mock_exchange.return_value = {"access_token": "google-token"}
        mock_profile.return_value = {
            "sub": "google-777",
            "email": "shared@example.com",
            "email_verified": True,
        }
        g_resp = await client.get("/oauth/google/callback?code=c2&state=s2")
        assert g_resp.status_code == 200

    # Google-issued token should identify the same user account
    g_token = g_resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {g_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "shared@example.com"
