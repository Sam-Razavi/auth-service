# Auth Service

Standalone authentication microservice for ApplyLuma, Rostid, and future projects.
Other apps delegate all auth to this service — they never handle passwords or tokens themselves.

## What's built (Phase 1)

- JWT access tokens (HS256, 15-minute lifetime)
- Refresh token rotation — old token revoked the moment a new pair is issued
- Redis blacklist for immediate access-token revocation on logout-all
- Register, login, logout (single device + all devices), `/me`
- Async SQLAlchemy + PostgreSQL + Alembic migrations
- Full test suite (20 tests, in-memory SQLite, Redis mocked)

## Roadmap

| Phase | Status | Content |
|-------|--------|---------|
| 1 — Core JWT | **Done** | Register, login, refresh, logout, /me |
| 2 — OAuth2 | Planned | GitHub + Google login |
| 3 — RBAC | Planned | Roles, admin endpoints |
| 4 — Password reset | Planned | Email-based forgot/reset flow |
| 5 — Polish | Planned | Rate limiting, logging, CI, GHCR image |

---

## Quick start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY to a random 32+ char string
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

The service starts on **http://localhost:8001**.
OpenAPI docs: **http://localhost:8001/docs**

### 3. Run migrations (first time only, if running without Docker)

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 4. Run tests

```bash
pytest tests/ -v
```

No running database needed — tests use in-memory SQLite with a Redis mock.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | Yes | — | `redis://host:6379` |
| `SECRET_KEY` | Yes | — | Min 32 chars, random, keep secret |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | Refresh token lifetime |
| `ENVIRONMENT` | No | `development` | Set to `production` to silence SQL echo |

---

## API reference

### Health

```
GET /health
→ {"status": "ok", "version": "1.0.0"}
```

### Auth endpoints

| Method | Path | Auth | Body | Returns |
|--------|------|------|------|---------|
| `POST` | `/auth/register` | None | `{email, password}` | `201 UserResponse` |
| `POST` | `/auth/login` | None | `{email, password}` | `200 TokenPair` |
| `POST` | `/auth/refresh` | None | `{refresh_token}` | `200 TokenPair` |
| `POST` | `/auth/logout` | None | `{refresh_token}` | `204` |
| `POST` | `/auth/logout-all` | Bearer | — | `204` |
| `GET`  | `/auth/me` | Bearer | — | `200 UserResponse` |

**TokenPair response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "a3f9...",
  "token_type": "bearer"
}
```

**UserResponse:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-09-03T09:00:00Z"
}
```

---

## How ApplyLuma and Rostid integrate

These apps have no auth logic of their own. Every protected route does:

```
GET /auth/me
Authorization: Bearer <access_token_from_cookie_or_header>
```

**200** → token valid, response body is the user object — use it to identify the caller.  
**401** → token expired or revoked → redirect user to login.

When the access token expires (15 min), the frontend uses the refresh token:

```
POST /auth/refresh
Content-Type: application/json
{"refresh_token": "<stored_refresh_token>"}
```

Store the new token pair, discard the old refresh token (it's already revoked).

**Never send the refresh token to ApplyLuma/Rostid's backend.** Keep it in the browser (httpOnly cookie recommended) and send it only to this service.

---

## Security notes

- Raw passwords are never stored or logged; bcrypt is applied before the value touches the database
- Refresh tokens are stored as SHA-256 hashes only; the raw token leaves the service exactly once (in the login/refresh response)
- Access token JTIs are blacklisted in Redis on `logout-all` for the token's remaining lifetime
- All secrets are loaded from environment variables; nothing is hardcoded
