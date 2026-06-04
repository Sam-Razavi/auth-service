import pytest


async def _register_and_login(client, email="user@example.com", password="pass1234"):
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()


async def test_refresh_returns_new_token_pair(client):
    tokens = await _register_and_login(client, "rot1@example.com")
    old_refresh = tokens["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != old_refresh


async def test_old_refresh_token_is_rejected_after_rotation(client):
    tokens = await _register_and_login(client, "rot2@example.com")
    old_refresh = tokens["refresh_token"]

    await client.post("/auth/refresh", json={"refresh_token": old_refresh})

    resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


async def test_invalid_refresh_token_rejected(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client):
    tokens = await _register_and_login(client, "logout1@example.com")
    refresh = tokens["refresh_token"]

    logout_resp = await client.post("/auth/logout", json={"refresh_token": refresh})
    assert logout_resp.status_code == 204

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


async def test_logout_all_revokes_all_refresh_tokens(client):
    tokens1 = await _register_and_login(client, "logall@example.com")
    # Second login creates a second refresh token for the same user
    tokens2_resp = await client.post("/auth/login", json={"email": "logall@example.com", "password": "pass1234"})
    tokens2 = tokens2_resp.json()

    # Logout all devices using first access token
    resp = await client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens1['access_token']}"},
    )
    assert resp.status_code == 204

    # Both refresh tokens must now be invalid
    r1 = await client.post("/auth/refresh", json={"refresh_token": tokens1["refresh_token"]})
    r2 = await client.post("/auth/refresh", json={"refresh_token": tokens2["refresh_token"]})
    assert r1.status_code == 401
    assert r2.status_code == 401


async def test_logout_all_requires_valid_token(client):
    resp = await client.post("/auth/logout-all", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401
