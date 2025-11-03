# Auth Service

Standalone authentication microservice for ApplyLuma, Rostid, and future projects.
Other apps delegate all auth to this service — they never handle passwords or tokens themselves.

## What's built

| Phase | Status | Content |
|-------|--------|---------|
| 1 — Core JWT | **Done** | Register, login, refresh, logout, /me |
| 2 — OAuth2 | **Done** | GitHub + Google login, account linking |
| 3 — RBAC | Planned | Roles, admin endpoints |
| 4 — Password reset | Planned | Email-based forgot/reset flow |
| 5 — Polish | Planned | Rate limiting, logging, CI, GHCR image |

**Phase 1 features:**
- JWT access tokens (HS256, 15-minute lifetime)
- Refresh token rotation — old token revoked the moment a new pair is issued
- Redis blacklist for immediate access-token revocation on logout-all
- Register, login, logout (single device + all devices), `/me`

**Phase 2 features:**
- GitHub OAuth2 — authorization code flow, private-email fallback
- Google OAuth2 — authorization code flow with OpenID Connect
- CSRF protection via single-use state tokens stored in Redis (10-minute TTL)
- `oauth_accounts` table links multiple providers to one user account
- OAuth-created users are marked `is_verified=True` automatically

---

## Quick start

### 1. Clone and configure

```bash
cp .env.example .env
# Required: SECRET_KEY (32+ random chars)
# For OAuth: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

The service starts on **http://localhost:8001**.
OpenAPI docs: **http://localhost:8001/docs**

### 3. Run migrations (first time, without Docker)

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 4. Run tests

```bash
pytest tests/ -v
```

No running database or Redis needed — tests use in-memory SQLite and a mocked Redis client.

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
| `GITHUB_CLIENT_ID` | Phase 2 | — | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | Phase 2 | — | GitHub OAuth app client secret |
| `GITHUB_REDIRECT_URI` | Phase 2 | `…/oauth/github/callback` | Must match GitHub app settings |
| `GOOGLE_CLIENT_ID` | Phase 2 | — | Google Cloud OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Phase 2 | — | Google Cloud OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Phase 2 | `…/oauth/google/callback` | Must match Google Cloud Console |
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

### OAuth endpoints

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/oauth/github` | `307` redirect to GitHub |
| `GET` | `/oauth/github/callback?code=…&state=…` | `200 TokenPair` |
| `GET` | `/oauth/google` | `307` redirect to Google |
| `GET` | `/oauth/google/callback?code=…&state=…` | `200 TokenPair` |

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

## OAuth2 setup

### GitHub

1. Go to **GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App**
2. Set **Authorization callback URL** to `http://localhost:8001/oauth/github/callback`
3. Copy **Client ID** and **Client Secret** into `.env`

### Google

1. Go to **Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client**
2. Add `http://localhost:8001/oauth/google/callback` as an **Authorized redirect URI**
3. Copy **Client ID** and **Client Secret** into `.env`

### OAuth flow in browser apps (ApplyLuma / Rostid)

```
Browser → GET /oauth/github
       ← 307 redirect to github.com
Browser → GitHub login
       ← redirect to /oauth/github/callback?code=…&state=…
       ← 200 {"access_token": "…", "refresh_token": "…"}
```

The callback returns JSON. Your frontend should intercept the callback URL,
read the JSON body, and store the token pair. The access token then works
identically to one issued by `/auth/login`.

**Account linking:** if the GitHub/Google email matches an existing password-based
account, the OAuth login is automatically linked to that account — the user ends
up with one account accessible via both methods.

---

## How ApplyLuma and Rostid integrate

These apps have no auth logic of their own. Every protected route does:

```
GET /auth/me
Authorization: Bearer <access_token>
```

**200** → token valid, response body is the user object.  
**401** → token expired or revoked → redirect user to login.

When the access token expires (15 min), the frontend refreshes it:

```
POST /auth/refresh
Content-Type: application/json
{"refresh_token": "<stored_refresh_token>"}
```

Store the new token pair, discard the old refresh token (it's immediately revoked on rotation).

**Never send the refresh token to your app's own backend.** Keep it in the browser
(httpOnly cookie recommended) and send it only to this service.

---

## Security notes

- Raw passwords are never stored or logged; bcrypt is applied before the value touches the database
- Refresh tokens are stored as SHA-256 hashes only; the raw token leaves the service exactly once
- Access token JTIs are blacklisted in Redis on `logout-all` for the token's remaining lifetime
- OAuth state tokens are single-use and expire after 10 minutes; reuse or forgery returns 400
- All secrets are loaded from environment variables; nothing is hardcoded
