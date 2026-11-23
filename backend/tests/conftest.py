import os
import sys
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set testing environment variable
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://deva_user:deva_password@localhost:5433/deva_test"

from app.main import app
from app.core.config import get_settings


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    settings = get_settings()
    settings.TESTING = True
    settings.ENVIRONMENT = "testing"
    settings.LLM_PROVIDER = "mock"
    settings.DATABASE_URL = "postgresql+asyncpg://deva_user:deva_password@localhost:5433/deva_test"
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
