"""
Database session factory with connection pooling.

Provides async SQLAlchemy session management for FastAPI
with configurable connection pooling for production use.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from server.config import server_config
from server.db.models import Base
from server.exceptions import DatabaseError, ErrorCode

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
async_session: async_sessionmaker | None = None


def _create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling."""
    db_url = server_config.database.url
    
    # Use NullPool for SQLite in-memory (better for testing)
    if "sqlite" in db_url and "memory" in db_url:
        poolclass = NullPool
        echo = server_config.database.echo
        engine = create_async_engine(db_url, echo=echo, poolclass=poolclass)
        logger.info(f"Created SQLite in-memory engine with NullPool")
    else:
        # Use QueuePool for production databases (PostgreSQL, MySQL)
        engine = create_async_engine(
            db_url,
            echo=server_config.database.echo,
            poolclass=QueuePool,
            pool_size=server_config.database.pool_size,
            max_overflow=server_config.database.max_overflow,
            pool_timeout=server_config.database.pool_timeout,
            pool_recycle=server_config.database.pool_recycle,
            connect_args={
                "timeout": server_config.database.pool_timeout,
                "check_same_thread": False,  # For SQLite
            },
        )
        logger.info(
            f"Created engine with QueuePool: "
            f"pool_size={server_config.database.pool_size}, "
            f"max_overflow={server_config.database.max_overflow}, "
            f"pool_timeout={server_config.database.pool_timeout}s, "
            f"pool_recycle={server_config.database.pool_recycle}s"
        )
    
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if not async_session:
        raise DatabaseError(
            "Database not initialized. Call init_db() first.",
            ErrorCode.DB_CONNECT_FAILED,
        )
    
    async with async_session() as session:
        try:
            yield session  # type: ignore[misc]
        except Exception as e:
            logger.error(f"Database session error: {e}")
            raise DatabaseError(
                "Database session error",
                ErrorCode.DB_QUERY_FAILED,
                {"details": str(e)},
            )
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database: create tables and session factory."""
    global engine, async_session
    
    try:
        engine = _create_engine()
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(
            f"Failed to initialize database: {e}",
            ErrorCode.DB_CONNECT_FAILED,
            {"details": str(e)},
        )


async def close_db() -> None:
    """Close the database engine and cleanup connections."""
    global engine
    
    if engine:
        try:
            await engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
