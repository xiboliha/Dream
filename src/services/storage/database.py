"""Database service for SQLAlchemy operations."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Type, TypeVar

from loguru import logger
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.user import Base as UserBase
from src.models.conversation import Base as ConversationBase
from src.models.memory import Base as MemoryBase

T = TypeVar("T")


class DatabaseService:
    """Database service for managing SQLAlchemy connections and sessions."""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
    ):
        """Initialize database service.

        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements
        """
        self.database_url = database_url
        self.echo = echo

        # Convert sqlite URL for async if needed
        if database_url.startswith("sqlite:///"):
            self.async_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        else:
            self.async_url = database_url

        # Sync engine and session (for migrations and simple operations)
        self.engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        # Async engine and session
        self.async_engine = create_async_engine(
            self.async_url,
            echo=echo,
        )
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"Database service initialized with URL: {database_url}")

    def create_tables(self) -> None:
        """Create all database tables."""
        UserBase.metadata.create_all(bind=self.engine)
        ConversationBase.metadata.create_all(bind=self.engine)
        MemoryBase.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        MemoryBase.metadata.drop_all(bind=self.engine)
        ConversationBase.metadata.drop_all(bind=self.engine)
        UserBase.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")

    def get_session(self) -> Session:
        """Get a synchronous database session."""
        return self.SessionLocal()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an asynchronous database session."""
        session = self.AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """Close database connections."""
        await self.async_engine.dispose()
        self.engine.dispose()
        logger.info("Database connections closed")


# Global database instance
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get the global database service instance."""
    global _db_service
    if _db_service is None:
        raise RuntimeError("Database service not initialized. Call init_database() first.")
    return _db_service


def init_database(database_url: str, echo: bool = False) -> DatabaseService:
    """Initialize the global database service."""
    global _db_service
    _db_service = DatabaseService(database_url, echo)
    _db_service.create_tables()
    return _db_service


async def close_database() -> None:
    """Close the global database service."""
    global _db_service
    if _db_service:
        await _db_service.close()
        _db_service = None
