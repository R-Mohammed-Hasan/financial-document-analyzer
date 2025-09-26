"""
SQLAlchemy declarative base and database utilities.

This module provides the base class for SQLAlchemy models and common database utilities.
"""

from typing import Any, Dict, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core.config import settings

# Create SQLAlchemy engine (sync for migrations)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create async engine for async operations
# Handle different database types properly
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support async with asyncpg, use aiosqlite
    async_database_url = settings.DATABASE_URL.replace(
        "sqlite://", "sqlite+aiosqlite://"
    )
    async_engine = create_async_engine(
        async_database_url, echo=settings.DEBUG, future=True
    )
else:
    # PostgreSQL async engine
    async_database_url = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    async_engine = create_async_engine(
        async_database_url,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        future=True,
    )

# Create session factory (sync for migrations)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base(metadata=MetaData(schema=None))

# Naming convention for database constraints
Base.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def get_db() -> Session:
    """
    Dependency function to get database session.

    Yields:
        Database session

    Usage:
        def some_endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


async def create_tables_async() -> None:
    """Create all database tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def drop_tables() -> None:
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


def get_database_url() -> str:
    """Get the database URL with sensitive data masked."""
    return settings.DATABASE_URL.replace(
        (
            settings.DATABASE_URL.split("://")[1].split("@")[0]
            if "@" in settings.DATABASE_URL
            else ""
        ),
        "***:***",
    )


def check_database_connection() -> Dict[str, Any]:
    """
    Check database connection and return status information.

    Returns:
        Dictionary with connection status and metadata
    """
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()

        return {
            "status": "connected",
            "database_url": get_database_url(),
            "engine": str(engine),
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "invalid": engine.pool.invalid(),
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "database_url": get_database_url()}


class DatabaseManager:
    """
    Database manager class for handling database operations.

    Provides methods for common database operations and maintenance.
    """

    def __init__(self, session: Session):
        """Initialize database manager with session."""
        self.session = session

    def commit(self) -> None:
        """Commit current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.session.rollback()

    def refresh(self, instance) -> None:
        """Refresh instance from database."""
        self.session.refresh(instance)

    def expire(self, instance) -> None:
        """Expire instance from session."""
        self.session.expire(instance)

    def add(self, instance) -> None:
        """Add instance to session."""
        self.session.add(instance)

    def add_all(self, instances) -> None:
        """Add multiple instances to session."""
        self.session.add_all(instances)

    def delete(self, instance) -> None:
        """Delete instance from session."""
        self.session.delete(instance)

    def merge(self, instance):
        """Merge instance with session."""
        return self.session.merge(instance)

    def flush(self) -> None:
        """Flush pending changes to database."""
        self.session.flush()

    def get(self, model_class, id_value):
        """Get instance by ID."""
        return self.session.get(model_class, id_value)

    def query(self, model_class):
        """Create query for model class."""
        return self.session.query(model_class)

    def execute(self, statement):
        """Execute raw SQL statement."""
        return self.session.execute(statement)

    def close(self) -> None:
        """Close database session."""
        self.session.close()
