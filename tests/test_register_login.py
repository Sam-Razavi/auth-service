from unittest.mock import AsyncMock


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"


async def test_register_success(client):
    resp = await client.post("/auth/register", json={"email": "alice@example.com", "password": "secret123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "secret123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


async def test_register_invalid_email(client):
    resp = await client.post("/auth/register", json={"email": "not-an-email", "password": "secret123"})
    assert resp.status_code == 422


async def test_login_success(client):
    await client.post("/auth/register", json={"email": "bob@example.com", "password": "pass1234"})
    resp = await client.post("/auth/login", json={"email": "bob@example.com", "password": "pass1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "carol@example.com", "password": "correct"})
    resp = await client.post("/auth/login", json={"email": "carol@example.com", "password": "wrong"})
    assert resp.status_code == 401


async def test_login_unknown_email(client):
    resp = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert resp.status_code == 401


async def test_me_returns_current_user(client):
    await client.post("/auth/register", json={"email": "dave@example.com", "password": "pass1234"})
    login = await client.post("/auth/login", json={"email": "dave@example.com", "password": "pass1234"})
    token = login.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "dave@example.com"


async def test_me_without_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403


async def test_me_with_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer totally.invalid.token"})
    assert resp.status_code == 401


async def test_account_locked_after_max_attempts(client, mock_redis):
    await client.post("/auth/register", json={"email": "lockme@example.com", "password": "pass1234"})
    # Simulate counter already at max
    mock_redis.incr = AsyncMock(return_value=6)  # over _MAX_ATTEMPTS=5
    resp = await client.post("/auth/login", json={"email": "lockme@example.com", "password": "pass1234"})
    assert resp.status_code == 401


async def test_successful_login_within_attempts_succeeds(client, mock_redis):
    await client.post("/auth/register", json={"email": "ok@example.com", "password": "pass1234"})
    mock_redis.incr = AsyncMock(return_value=3)  # within limit
    resp = await client.post("/auth/login", json={"email": "ok@example.com", "password": "pass1234"})
    assert resp.status_code == 200
