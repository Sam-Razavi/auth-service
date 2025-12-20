from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.role import Role  # noqa: F401 — ensures table is registered in metadata

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Fresh in-memory SQLite database per test, using StaticPool for single-connection isolation."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def mock_redis():
    """Replace Redis with an in-memory mock for all tests."""
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.delete = AsyncMock(return_value=1)  # default: OAuth state is valid

    async def fake_get_redis():
        return redis_mock

    with patch("app.utils.redis.get_redis", side_effect=fake_get_redis):
        yield redis_mock


@pytest.fixture(autouse=True)
def mock_email_service():
    """Prevent any real SMTP calls in tests; yield mocks so tests can inspect calls."""
    with (
        patch(
            "app.services.email_service.send_password_reset_email",
            new_callable=AsyncMock,
        ) as mock_reset,
        patch(
            "app.services.email_service.send_verification_email",
            new_callable=AsyncMock,
        ) as mock_verify,
    ):
        yield {"reset": mock_reset, "verify": mock_verify}


@pytest_asyncio.fixture
async def roles(db) -> dict[str, Role]:
    """Seed the three default roles into the test database."""
    admin = Role(name="admin")
    user_role = Role(name="user")
    mod = Role(name="moderator")
    db.add_all([admin, user_role, mod])
    await db.commit()
    return {"admin": admin, "user": user_role, "moderator": mod}


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
