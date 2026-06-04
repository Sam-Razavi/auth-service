import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, oauth, admin
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.ENVIRONMENT)
log = get_logger(__name__)

app = FastAPI(
    title="Auth Service",
    version="1.0.0",
    description="Standalone authentication microservice for ApplyLuma, Rostid, and future apps.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(admin.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
