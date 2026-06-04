# Auth Service

![Tests](https://github.com/Sam-Razavi/auth-service/actions/workflows/test.yml/badge.svg)
![Docker](https://github.com/Sam-Razavi/auth-service/actions/workflows/docker.yml/badge.svg)

Standalone authentication microservice for **ApplyLuma**, **Rostid**, and any future service that needs auth.

Apps that use this service delegate all authentication and session management here — they never handle passwords, tokens, or OAuth flows themselves. Any protected route just calls `GET /auth/validate` with the Bearer token and gets the user object back.

---

## Features

### Identity & Sessions
- **JWT access tokens** (HS256, 15-minute lifetime)
- **Refresh token rotation** — the moment a new pair is issued the old refresh token is revoked; replayed tokens are rejected
- **Redis blacklist** — `logout-all` immediately invalidates the access token for all devices without waiting for expiry
- **Account lockout** — 5 consecutive failed login attempts locks the account for 15 minutes (Redis counter, auto-expires)

### OAuth2
- **GitHub** and **Google** login via authorization-code flow
- **Private-email fallback** for GitHub accounts with hidden email addresses
- **CSRF protection** — single-use state tokens stored in Redis with a 10-minute TTL
- **Account linking** — OAuth logins are automatically merged with an existing password account on the same email

### Role-based Access Control
- `admin`, `user`, `moderator` roles — many-to-many via `user_roles` table
- `require_role()` Depends factory — attach to any route to enforce a minimum role
- Admin endpoints for listing users, assigning roles, and soft-deactivating accounts
- Roles seeded automatically by Alembic migration

### Password & Email Flows
- **Email verification** sent on registration; resend endpoint available
- **Forgot / reset password** with one-hour single-use token
- **Set password** endpoint lets OAuth-only users add a local password
- Tokens stored as SHA-256 hashes with `used_at` tracking — each token works exactly once
- SMTP via stdlib `smtplib` with STARTTLS; falls back to console output when `SMTP_HOST` is unset

### Security Hardening
- Password complexity enforced everywhere — minimum 8 characters, at least one letter and one digit or special character
- Security response headers on every request: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`
- Flat, consistent error responses — no stack traces ever exposed to clients
- Structured `audit.*` log events on every key action (register, login, logout, password reset, email verification)

### Observability
- **Structured JSON logging** with `structlog` — JSON in production, colored output in development
- **`X-Request-ID`** header on every response — echoes caller-supplied IDs or generates a UUID; bound to structlog context for log correlation
- **`Retry-After`** header on all 429 rate-limit responses
- **Deep `/health`** endpoint checks DB and Redis, returns 503 if either is down
- **CI coverage gate** — pytest-cov enforces 70% minimum line coverage

### Reliability
- Per-IP rate limiting backed by Redis: login 10/min, register 5/min, forgot-password 3/5min
- Docker healthchecks on all three services (`app`, `postgres`, `redis`)
- `app` waits for both postgres and redis to be healthy before starting
- Configurable CORS origins via `ALLOWED_ORIGINS` env var

---

## Quick start

### Run with Docker Compose

```bash
cp .env.example .env
# Fill in SECRET_KEY (32+ random chars)
# Optional: GITHUB_CLIENT_ID/SECRET, GOOGLE_CLIENT_ID/SECRET, SMTP_HOST/USER/PASSWORD

docker-compose up --build
```

The service starts on **http://localhost:8001**.  
Interactive API docs: **http://localhost:8001/docs**

### Run locally (without Docker)

```bash
pip install -r requirements.txt

# Point DATABASE_URL at a local postgres (or use SQLite for quick testing):
export DATABASE_URL=sqlite+aiosqlite:///./dev.db
export REDIS_URL=redis://localhost:6379
export SECRET_KEY=change-me-to-something-random-32-chars

alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

### Run tests

```bash
pytest tests/ -v
```

No live database or Redis needed — tests use in-memory SQLite and a mock Redis client.

---

## API reference

### Health

```
GET /health
→ 200 {"status": "ok",       "version": "1.0.0", "checks": {"database": "ok", "redis": "ok"}}
→ 503 {"status": "degraded", "version": "1.0.0", "checks": {"database": "error", "redis": "ok"}}
```

### Auth

| Method | Path | Auth | Body | Returns |
|--------|------|------|------|---------|
| `POST` | `/auth/register` | — | `{email, password}` | `201 UserResponse` |
| `POST` | `/auth/login` | — | `{email, password}` | `200 TokenPair` |
| `POST` | `/auth/refresh` | — | `{refresh_token}` | `200 TokenPair` |
| `POST` | `/auth/logout` | — | `{refresh_token}` | `204` |
| `POST` | `/auth/logout-all` | Bearer | — | `204` |
| `GET`  | `/auth/me` | Bearer | — | `200 UserResponse` |
| `GET`  | `/auth/validate` | Bearer | — | `200 UserResponse` |

`/auth/validate` is the service-to-service introspection endpoint. Downstream apps call it to confirm a token is valid and get the user object (including roles) in one request.

### Password reset & email verification

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `POST` | `/auth/forgot-password` | `{email}` | `200` (always — prevents enumeration) |
| `POST` | `/auth/reset-password` | `{token, new_password}` | `200` or `400` |
| `POST` | `/auth/verify-email/{token}` | — | `200` or `400` |
| `POST` | `/auth/verify-email/resend` | `{email}` | `200` (always) |
| `POST` | `/auth/set-password` | `{new_password}` | `200` or `409` |

A successful password reset immediately revokes all refresh tokens across all devices.

`set-password` returns `409` if the account already has a password — use `forgot-password` to change it.

### OAuth

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/oauth/github` | `307` redirect to GitHub |
| `GET` | `/oauth/github/callback?code=…&state=…` | `200 TokenPair` |
| `GET` | `/oauth/google` | `307` redirect to Google |
| `GET` | `/oauth/google/callback?code=…&state=…` | `200 TokenPair` |

### Admin (requires `admin` role)

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `GET` | `/admin/users?skip=0&limit=50` | — | `200 list[UserResponse]` |
| `GET` | `/admin/users/{id}` | — | `200 UserResponse` or `404` |
| `PUT` | `/admin/users/{id}/roles` | `{roles: [...]}` | `200 UserResponse` |
| `DELETE` | `/admin/users/{id}` | — | `204` or `404` |

Role assignment fully replaces the current set. Pass `{"roles": []}` to remove all roles.

### Response shapes

```json
// TokenPair
{
  "access_token": "eyJ...",
  "refresh_token": "a3f9c1...",
  "token_type": "bearer"
}

// UserResponse
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "user@example.com",
  "is_active": true,
  "is_verified": true,
  "created_at": "2025-09-03T09:00:00Z",
  "roles": ["admin"]
}
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pass@host/db` (prod) or `sqlite+aiosqlite:///./dev.db` (dev) |
| `REDIS_URL` | Yes | — | `redis://host:6379` |
| `SECRET_KEY` | Yes | — | Min 32 chars, random, keep secret |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | Refresh token lifetime in days |
| `ALLOWED_ORIGINS` | No | `["*"]` | JSON list of allowed CORS origins |
| `ENVIRONMENT` | No | `development` | Set to `production` for JSON logs and no SQL echo |
| `GITHUB_CLIENT_ID` | OAuth | — | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | OAuth | — | GitHub OAuth app client secret |
| `GITHUB_REDIRECT_URI` | OAuth | `/oauth/github/callback` | Must match GitHub app settings |
| `GOOGLE_CLIENT_ID` | OAuth | — | Google Cloud OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth | — | Google Cloud OAuth client secret |
| `GOOGLE_REDIRECT_URI` | OAuth | `/oauth/google/callback` | Must match Google Cloud Console |
| `SMTP_HOST` | Email | `""` | SMTP server hostname; empty = log emails to stdout |
| `SMTP_PORT` | Email | `587` | SMTP port (STARTTLS) |
| `SMTP_USER` | Email | `""` | SMTP username |
| `SMTP_PASSWORD` | Email | `""` | SMTP password |
| `FROM_EMAIL` | Email | `noreply@yourdomain.com` | Sender address |
| `APP_URL` | Email | `http://localhost:8001` | Base URL used in email links |

---

## Integrating downstream services

Any service that uses this auth service needs to do exactly two things:

**1. Verify a token and get the user**

```http
GET /auth/validate
Authorization: Bearer <access_token>
```

`200` → token valid, body is the user object including roles.  
`401` → token expired or revoked → send the user to login.

**2. Refresh an expired access token**

```http
POST /auth/refresh
Content-Type: application/json

{"refresh_token": "<stored_refresh_token>"}
```

Store the new token pair, discard the old one (it's revoked the moment rotation happens).

> Keep the refresh token out of your app's backend. Store it in the browser (httpOnly cookie recommended) and send it only to this service.

### Checking roles

The `roles` array in the user object is the source of truth. Example in Python:

```python
resp = httpx.get(
    "http://auth-service/auth/validate",
    headers={"Authorization": f"Bearer {token}"},
)
if resp.status_code != 200:
    raise Unauthorized()
user = resp.json()
if "admin" not in user["roles"]:
    raise Forbidden()
```

---

## OAuth2 setup

### GitHub

1. **GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App**
2. Set **Authorization callback URL** to `https://your-domain/oauth/github/callback`
3. Copy **Client ID** and **Client Secret** into `.env`

### Google

1. **Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client ID**
2. Add `https://your-domain/oauth/google/callback` as an **Authorized redirect URI**
3. Copy **Client ID** and **Client Secret** into `.env`

### OAuth flow for browser apps

```
Browser  →  GET /oauth/github
         ←  307 redirect to github.com
Browser  →  User grants access on GitHub
         ←  redirect to /oauth/github/callback?code=…&state=…
         ←  200 {"access_token": "…", "refresh_token": "…"}
```

The callback returns JSON. Your frontend intercepts the callback URL, reads the token pair from the body, and stores it — from that point on the token is identical to one issued by `/auth/login`.

---

## Rate limits

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 10 requests / 60 s |
| `POST /auth/register` | 5 requests / 60 s |
| `POST /auth/forgot-password` | 3 requests / 300 s |

Limits are per client IP. Exceeding a limit returns `429 Too Many Requests` with a `Retry-After` header (seconds to wait).

---

## Request tracing

Every response carries an `X-Request-ID` header. If the caller includes `X-Request-ID: <your-uuid>` in the request, the same value is echoed back — useful for correlating browser/mobile logs with server logs in production.

---

## Security notes

- Raw passwords are **never** stored or logged; bcrypt is applied before the value touches the database
- Refresh tokens are stored as **SHA-256 hashes** only; the raw token leaves the service exactly once
- Access token JTIs are blacklisted in Redis on `logout-all` for the token's remaining lifetime
- OAuth state tokens are single-use and expire after 10 minutes; reuse or forgery returns 400
- Password reset and verification tokens are SHA-256 hashed, expire, and can only be used once
- `forgot-password` and `verify-email/resend` always return 200 regardless of whether the address exists
- Successful password reset revokes all refresh tokens on all devices immediately
- Account lockout: 5 failed attempts → 15-minute Redis lock (same response as wrong credentials — no enumeration)
- Security headers on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`
- Unhandled server errors return `{"detail": "Internal server error"}` — stack traces are never sent to clients
- All secrets come from environment variables; nothing is hardcoded
- Key auth events emit `audit.*` structlog entries for monitoring and alerting

---

## Project structure

```
app/
├── main.py                  # FastAPI app, middleware registration, exception handlers
├── config.py                # Settings (pydantic-settings, lru_cache singleton)
├── database.py              # Async SQLAlchemy engine + get_db dependency
├── dependencies/
│   └── auth.py              # get_current_user — decodes JWT, checks blacklist
├── middleware/
│   ├── rate_limit.py        # Per-IP rate limiting backed by Redis
│   ├── request_id.py        # X-Request-ID header + structlog context binding
│   └── security_headers.py  # Security response headers
├── models/
│   ├── user.py              # User table
│   ├── token.py             # RefreshToken table
│   ├── role.py              # Role + UserRole tables
│   └── reset_token.py       # PasswordResetToken table (shared for pw-reset + email-verify)
├── routers/
│   ├── auth.py              # All /auth/* endpoints
│   ├── oauth.py             # /oauth/github and /oauth/google
│   └── admin.py             # /admin/* endpoints
├── schemas/                 # Pydantic v2 request/response models
├── services/
│   ├── auth_service.py      # register_user, authenticate_user (with lockout)
│   ├── token_service.py     # create_token_pair, rotate, revoke, revoke-all
│   ├── password_reset_service.py  # reset + email-verification flows
│   ├── email_service.py     # SMTP sender (async via run_in_executor)
│   ├── oauth_service.py     # GitHub + Google OAuth helpers
│   └── admin_service.py     # Admin CRUD operations
└── utils/
    ├── security.py          # hash_password, verify_password, JWT helpers
    ├── redis.py             # Redis client singleton, blacklist helpers
    └── logging.py           # structlog configuration

alembic/versions/            # Database migrations
tests/                       # pytest suite (in-memory SQLite + mock Redis)
```

---

## Development workflow

```bash
# Create a migration after changing models
alembic revision --autogenerate -m "describe the change"
alembic upgrade head

# Run only the tests relevant to what you changed
pytest tests/test_register_login.py -v

# Check coverage
pytest tests/ --cov=app --cov-report=term-missing
```
