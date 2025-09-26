"""
Database session management and dependency injection.

This module provides database session handling and dependency injection utilities.
"""

from typing import Generator, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status

from db.base import SessionLocal, AsyncSessionLocal, DatabaseManager


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    This function provides a database session that is automatically
    closed after the request is processed.

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


def get_database_manager(db: Session = Depends(get_db)) -> DatabaseManager:
    """
    Dependency function to get database manager.

    Args:
        db: Database session

    Returns:
        Database manager instance

    Usage:
        def some_endpoint(db_manager: DatabaseManager = Depends(get_database_manager)):
            # Use db_manager for database operations
            pass
    """
    return DatabaseManager(db)


def require_database_session() -> Session:
    """
    Require a valid database session.

    Returns:
        Database session

    Raises:
        HTTPException: If database session is not available
    """
    try:
        db = SessionLocal()
        # Test the connection
        db.execute("SELECT 1")
        return db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        )


def close_database_session(db: Session) -> None:
    """
    Close database session.

    Args:
        db: Database session to close
    """
    try:
        db.close()
    except Exception:
        # Ignore errors when closing
        pass


class DatabaseSessionManager:
    """
    Context manager for database sessions.

    Provides automatic session management with proper cleanup.
    """

    def __init__(self):
        """Initialize session manager."""
        self.db: Session = None

    def __enter__(self) -> "DatabaseSessionManager":
        """Enter context and create database session."""
        self.db = SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and close database session."""
        if self.db:
            try:
                if exc_type is not None:
                    # Rollback on exception
                    self.db.rollback()
                else:
                    # Commit on success
                    self.db.commit()
            except Exception:
                # Always rollback if commit fails
                self.db.rollback()
            finally:
                self.db.close()

    def get_session(self) -> Session:
        """Get the current database session."""
        if not self.db:
            raise RuntimeError("Database session not initialized. Use context manager.")
        return self.db

    def get_manager(self) -> DatabaseManager:
        """Get database manager for current session."""
        return DatabaseManager(self.get_session())


# Global session manager instance
session_manager = DatabaseSessionManager()


def transaction(func):
    """
    Decorator to wrap function in database transaction.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """

    def wrapper(*args, **kwargs):
        with DatabaseSessionManager() as session_mgr:
            try:
                result = func(session_mgr.get_session(), *args, **kwargs)
                return result
            except Exception:
                session_mgr.db.rollback()
                raise

    return wrapper


def readonly_transaction(func):
    """
    Decorator to wrap function in read-only database transaction.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """

    def wrapper(*args, **kwargs):
        with DatabaseSessionManager() as session_mgr:
            try:
                # Set session to read-only mode
                session_mgr.db.execute("SET TRANSACTION READ ONLY")
                result = func(session_mgr.get_session(), *args, **kwargs)
                return result
            except Exception:
                raise

    return wrapper


# Async session management functions
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.

    This function provides an async database session that is automatically
    closed after the request is processed.

    Yields:
        Async database session

    Usage:
        async def some_endpoint(db: AsyncSession = Depends(get_async_db)):
            # Use db session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_async_database_manager(
    db: AsyncSession = Depends(get_async_db),
) -> DatabaseManager:
    """
    Dependency function to get async database manager.

    Args:
        db: Async database session

    Returns:
        Database manager instance

    Usage:
        async def some_endpoint(db_manager: DatabaseManager = Depends(get_async_database_manager)):
            # Use db_manager for database operations
            pass
    """
    return DatabaseManager(db)


async def require_async_database_session() -> AsyncSession:
    """
    Require a valid async database session.

    Returns:
        Async database session

    Raises:
        HTTPException: If database session is not available
    """
    try:
        async with AsyncSessionLocal() as db:
            # Test the connection
            await db.execute("SELECT 1")
            return db
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        )


async def close_async_database_session(db: AsyncSession) -> None:
    """
    Close async database session.

    Args:
        db: Async database session to close
    """
    try:
        await db.close()
    except Exception:
        # Ignore errors when closing
        pass


class AsyncDatabaseSessionManager:
    """
    Async context manager for database sessions.

    Provides automatic session management with proper cleanup.
    """

    def __init__(self):
        """Initialize async session manager."""
        self.db: AsyncSession = None

    async def __aenter__(self) -> "AsyncDatabaseSessionManager":
        """Enter context and create async database session."""
        self.db = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and close async database session."""
        if self.db:
            try:
                if exc_type is not None:
                    # Rollback on exception
                    await self.db.rollback()
                else:
                    # Commit on success
                    await self.db.commit()
            except Exception:
                # Always rollback if commit fails
                await self.db.rollback()
            finally:
                await self.db.close()

    def get_session(self) -> AsyncSession:
        """Get the current async database session."""
        if not self.db:
            raise RuntimeError(
                "Async database session not initialized. Use async context manager."
            )
        return self.db

    def get_manager(self) -> DatabaseManager:
        """Get database manager for current async session."""
        return DatabaseManager(self.get_session())


# Global async session manager instance
async_session_manager = AsyncDatabaseSessionManager()


async def async_transaction(func):
    """
    Async decorator to wrap function in database transaction.

    Args:
        func: Async function to wrap

    Returns:
        Wrapped async function
    """

    async def wrapper(*args, **kwargs):
        async with AsyncDatabaseSessionManager() as session_mgr:
            try:
                result = await func(session_mgr.get_session(), *args, **kwargs)
                return result
            except Exception:
                await session_mgr.db.rollback()
                raise

    return wrapper


async def async_readonly_transaction(func):
    """
    Async decorator to wrap function in read-only database transaction.

    Args:
        func: Async function to wrap

    Returns:
        Wrapped async function
    """

    async def wrapper(*args, **kwargs):
        async with AsyncDatabaseSessionManager() as session_mgr:
            try:
                # Set session to read-only mode
                await session_mgr.db.execute("SET TRANSACTION READ ONLY")
                result = await func(session_mgr.get_session(), *args, **kwargs)
                return result
            except Exception:
                raise

    return wrapper
