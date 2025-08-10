"""
Database connection and session management utilities
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency for FastAPI
    
    Usage:
        @app.get("/users/")
        async def read_users(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session as context manager
    
    Usage:
        async with get_db_session() as db:
            # Use db session here
            result = await db.execute(query)
            await db.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and create tables if needed"""
    try:
        # Test the connection
        async with engine.begin() as conn:
            # You could create tables here if needed, but we use Alembic
            # await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


class DatabaseManager:
    """Database manager for handling connections and transactions"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """Check if database is healthy"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        return self.session_factory()
    
    async def execute_raw_sql(self, sql: str, params: dict = None):
        """Execute raw SQL query"""
        async with self.session_factory() as session:
            result = await session.execute(sql, params or {})
            await session.commit()
            return result


# Global database manager instance
db_manager = DatabaseManager()