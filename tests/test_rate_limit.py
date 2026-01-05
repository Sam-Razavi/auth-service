"""
Phase 5 — rate limiting tests.

The global mock_redis fixture sets incr to return 1 (well within all limits).
Individual tests override incr to simulate a limit breach.
"""
from unittest.mock import AsyncMock


async def test_login_within_limit_succeeds(client):
    resp = await client.post("/auth/login", json={"email": "x@example.com", "password": "pass"})
    # 401 (wrong creds) not 429 — rate limit was not triggered
    assert resp.status_code == 401


async def test_login_rate_limited_when_counter_exceeded(client, mock_redis):
    mock_redis.incr = AsyncMock(return_value=11)  # over the 10/min limit

    resp = await client.post("/auth/login", json={"email": "x@example.com", "password": "pass"})
    assert resp.status_code == 429
    assert "Too many requests" in resp.json()["detail"]


async def test_register_rate_limited_when_counter_exceeded(client, mock_redis):
    mock_redis.incr = AsyncMock(return_value=6)  # over the 5/min limit

    resp = await client.post(
        "/auth/register", json={"email": "x@example.com", "password": "pass1234"}
    )
    assert resp.status_code == 429


async def test_forgot_password_rate_limited_when_counter_exceeded(client, mock_redis):
    mock_redis.incr = AsyncMock(return_value=4)  # over the 3/5-min limit

    resp = await client.post("/auth/forgot-password", json={"email": "x@example.com"})
    assert resp.status_code == 429


async def test_unprotected_path_not_rate_limited(client, mock_redis):
    mock_redis.incr = AsyncMock(return_value=9999)  # would trigger any limit

    resp = await client.get("/health")
    assert resp.status_code == 200  # /health has no rate limit
