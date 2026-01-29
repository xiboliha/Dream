"""Pytest configuration and fixtures."""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./data/database/test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    from src.services.storage import init_database, close_database, get_database_service

    # Initialize test database
    init_database("sqlite:///./data/database/test.db", echo=False)
    db = get_database_service()

    async with db.get_async_session() as session:
        yield session

    # Cleanup
    await close_database()


@pytest.fixture
def mock_ai_response():
    """Mock AI response for testing."""
    return "这是一个测试回复~"


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "wechat_id": "test_user_123",
        "nickname": "测试用户",
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "content": "你好，今天天气怎么样？",
        "msg_id": "msg_123456",
    }
