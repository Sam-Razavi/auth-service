# Auth Service

![Tests](https://github.com/sam-razavi/auth-service/actions/workflows/test.yml/badge.svg)

Standalone authentication microservice for ApplyLuma, Rostid, and future projects.
Other apps delegate all auth to this service — they never handle passwords or tokens themselves.

## What's built

| Phase | Status | Content |
|-------|--------|---------|
| 1 — Core JWT | **Done** | Register, login, refresh, logout, /me |
| 2 — OAuth2 | **Done** | GitHub + Google login, account linking |
| 3 — RBAC | **Done** | Roles, admin endpoints, role assignment |
| 4 — Password reset | **Done** | Email verification, forgot/reset password flow |
| 5 — Polish | **Done** | Rate limiting, structured logging, CI, GHCR image |
| 6 — Hardening | **Done** | CORS config, deep health check, account lockout, security headers, token validation endpoint, Retry-After header, X-Request-ID tracing, coverage CI gate, Docker healthcheck, audit logging, standardized error responses |

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

**Phase 3 features:**
- Role-based access control (admin, user, moderator) via `roles` many-to-many table
- `require_role()` dependency factory — attach to any route to gate by role
- `/auth/me` now includes the user's assigned roles
- Admin-only endpoints: list users, get user, assign roles, deactivate user
- Default roles seeded via Alembic migration (no manual SQL needed)
- Soft-delete deactivation — deactivated users cannot log in

**Phase 5 features:**
- Per-IP rate limiting via `RateLimitMiddleware` backed by Redis: login 10/min, register 5/min, forgot-password 3/5min — returns 429
- Structured JSON logging with `structlog` — JSON in production, colored in development; all requests logged with method, path, status, and duration
- GitHub Actions CI — runs `pytest` on every push to `main` or a feature branch and on PRs
- Docker image built and pushed to GHCR (`ghcr.io/sam-razavi/auth-service`) on every push to `main` and on `v*` tags with automatic semver tagging

**Phase 6 features:**
- Configurable CORS origins via `ALLOWED_ORIGINS` env var
- Deep `/health` endpoint checks database and Redis connectivity, returns 503 when either is unhealthy
- `POST /auth/verify-email/resend` — resend a verification email to an unverified address
- Account lockout — 5 failed login attempts triggers a 15-minute lockout per email address (backed by Redis)
- `POST /auth/set-password` — allows OAuth-only users to add a local password
- Security headers middleware — `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`
- `GET /auth/validate` — service-to-service token introspection endpoint returning the user object
- `Retry-After` response header on 429 rate-limit responses
- `X-Request-ID` middleware — echoes or generates a UUID per request for distributed tracing; bound to structlog context
- CI coverage gate — `pytest-cov` enforces minimum 70% line coverage in CI
- Docker healthcheck for the `app` service via `/health` endpoint
- Structured audit log events (`audit.register`, `audit.login`, `audit.login_failed`, `audit.login_locked`, `audit.logout`, `audit.logout_all`, `audit.email_verified`, `audit.password_reset`)
- Global exception handlers — validation errors return a flat 422 body; uncaught exceptions return 500 without leaking tracebacks
- Password complexity enforced everywhere: minimum 8 characters, at least one letter and one digit or special character

**Phase 4 features:**
- Email verification sent automatically on registration; `POST /auth/verify-email/{token}` marks the user as verified
- `POST /auth/forgot-password` — sends a one-hour reset link; always returns 200 to prevent email enumeration
- `POST /auth/reset-password` — validates single-use token, updates the password, and revokes all active sessions
- Tokens stored as SHA-256 hashes with expiry and `used_at` tracking (single-use enforcement)
- SMTP via stdlib `smtplib` with STARTTLS; falls back to console logging when `SMTP_HOST` is unset (development mode)

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
| `SMTP_HOST` | Phase 4 | `""` | SMTP server hostname; leave empty to log emails to stdout |
| `SMTP_PORT` | Phase 4 | `587` | SMTP port (STARTTLS) |
| `SMTP_USER` | Phase 4 | `""` | SMTP username |
| `SMTP_PASSWORD` | Phase 4 | `""` | SMTP password |
| `FROM_EMAIL` | Phase 4 | `noreply@yourdomain.com` | Sender address for outbound emails |
| `APP_URL` | Phase 4 | `http://localhost:8001` | Base URL used in email links |
| `RATE_LIMIT_STORAGE_URL` | Phase 5 | `memory://` | Rate limit backend; set to `redis://…` in production |

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

### Password reset and email verification endpoints

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `POST` | `/auth/forgot-password` | `{"email": "…"}` | `200` always |
| `POST` | `/auth/reset-password` | `{"token": "…", "new_password": "…"}` | `200` or `400` |
| `POST` | `/auth/verify-email/{token}` | — | `200` or `400` |
| `POST` | `/auth/verify-email/resend` | `{"email": "…"}` | `200` always |
| `POST` | `/auth/set-password` | `{"new_password": "…"}` | `200` or `409` |
| `GET`  | `/auth/validate` | — | `200 UserResponse` or `401` |

`new_password` must be at least 8 characters, with at least one letter and one digit or special character. A successful reset revokes all existing refresh tokens, forcing re-login on all devices.

### Admin endpoints

All admin endpoints require a valid Bearer token from a user with the `admin` role.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `GET` | `/admin/users?skip=0&limit=50` | — | `200 list[UserResponse]` |
| `GET` | `/admin/users/{id}` | — | `200 UserResponse` or `404` |
| `PUT` | `/admin/users/{id}/roles` | `{"roles": ["moderator"]}` | `200 UserResponse` |
| `DELETE` | `/admin/users/{id}` | — | `204` or `404` |

Role assignment fully replaces the user's current role set. Pass `{"roles": []}` to clear all roles.

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
  "created_at": "2025-09-03T09:00:00Z",
  "roles": ["admin"]
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

## RBAC integration

### Assigning roles

Roles are assigned by an admin via `PUT /admin/users/{id}/roles`. There is no self-service endpoint — role changes must go through a user with the `admin` role.

### Protecting routes in downstream services

If your app delegates auth to this service, check the `roles` field returned by `GET /auth/me`:

```python
# Example: gate a route in ApplyLuma
me = requests.get("http://auth-service/auth/me", headers={"Authorization": f"Bearer {token}"})
if "admin" not in me.json().get("roles", []):
    return 403
```

### Seeded roles

Three roles are seeded automatically by the `alembic upgrade head` migration:

| Role | Purpose |
|------|---------|
| `admin` | Full access to `/admin/*` endpoints |
| `user` | Standard authenticated user (no special privileges) |
| `moderator` | Reserved for content moderation features (Phase 5) |

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

## Rate limits

The following endpoints are rate-limited per client IP:

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 10 requests / minute |
| `POST /auth/register` | 5 requests / minute |
| `POST /auth/forgot-password` | 3 requests / 5 minutes |

All other endpoints are unlimited. Breaching a limit returns `429 Too Many Requests` with a `Retry-After` header indicating how many seconds to wait.

In development (`RATE_LIMIT_STORAGE_URL=memory://`) counters are local to the process and reset on restart. In production, point this at Redis so limits are enforced consistently across multiple replicas.

---

## Request tracing

Every response includes an `X-Request-ID` header. If the caller sends `X-Request-ID: <uuid>` in the request, the same value is echoed back — useful for correlating client-side and server-side logs in distributed systems.

---

## Security notes

- Raw passwords are never stored or logged; bcrypt is applied before the value touches the database
- Refresh tokens are stored as SHA-256 hashes only; the raw token leaves the service exactly once
- Access token JTIs are blacklisted in Redis on `logout-all` for the token's remaining lifetime
- OAuth state tokens are single-use and expire after 10 minutes; reuse or forgery returns 400
- Password reset and verification tokens are SHA-256 hashed, expire after 1 hour / 24 hours respectively, and can only be used once (`used_at` tracking)
- `forgot-password` always returns 200 regardless of whether the email exists (prevents enumeration)
- Successful password reset immediately revokes all refresh tokens across all devices
- All secrets are loaded from environment variables; nothing is hardcoded
- Account lockout: 5 consecutive failed login attempts locks the account for 15 minutes (counter stored in Redis)
- Security response headers set on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`
- Unhandled server errors return `{"detail": "Internal server error"}` — stack traces are never exposed to clients
- Key auth events (register, login, logout, password reset, email verification) are emitted as structured `audit.*` log entries for security monitoring
