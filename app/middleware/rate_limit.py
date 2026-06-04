from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.utils.redis as _redis_utils

# (max_requests, window_seconds)
_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/login": (10, 60),
    "/auth/register": (5, 60),
    "/auth/forgot-password": (3, 300),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        config = _LIMITS.get(request.url.path)
        if config is None:
            return await call_next(request)

        max_requests, window_seconds = config
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{request.url.path}:{client_ip}"

        r = await _redis_utils.get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)

        if count > max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(window_seconds)},
            )

        return await call_next(request)
