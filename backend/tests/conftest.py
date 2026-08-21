import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.services.auth import AuthService
from app.config import get_settings


MERCHANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()

MOCK_USER = MagicMock()
MOCK_USER.id = USER_ID
MOCK_USER.email = "test@paypilot.ai"
MOCK_USER.full_name = "Test User"
MOCK_USER.role = "merchant_admin"
MOCK_USER.merchant_id = MERCHANT_ID
MOCK_USER.is_active = True


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    yield session


@pytest_asyncio.fixture
async def mock_db_dependency(mock_db_session):
    async def _get_db():
        try:
            yield mock_db_session
            await mock_db_session.commit()
        except Exception:
            await mock_db_session.rollback()
            raise
        finally:
            await mock_db_session.close()
    return _get_db


@pytest_asyncio.fixture
async def mock_auth_dependency():
    async def _get_current_user():
        return MOCK_USER
    return _get_current_user


@pytest_asyncio.fixture
async def test_client(mock_db_dependency, mock_auth_dependency):
    app.dependency_overrides[get_db] = mock_db_dependency
    app.dependency_overrides[get_current_user_dependency] = mock_auth_dependency
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(mock_db_dependency):
    app.dependency_overrides[get_db] = mock_db_dependency
    app.dependency_overrides.pop(get_current_user_dependency, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    token = AuthService.create_access_token(data={"sub": str(USER_ID)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_merchant_id():
    return MERCHANT_ID


@pytest.fixture
def test_user_id():
    return USER_ID
