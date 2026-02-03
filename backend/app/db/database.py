"""
Database Configuration and Session Management
Supports both SQLite (development) and PostgreSQL (production)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings
from pathlib import Path
from urllib.parse import urlparse


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Determine if using SQLite (for development without Docker/PostgreSQL)
is_sqlite = settings.database_url.startswith("sqlite")

# Create async engine with appropriate settings
if is_sqlite:
    # Ensure the parent directory for the SQLite file exists. This
    # avoids "unable to open database file" when the path's directory
    # hasn't been created or when running from a different CWD.
    try:
        parsed = urlparse(settings.database_url)
        db_path = parsed.path
        # On Windows urlparse yields a leading slash before drive letter: '/C:/...'
        if db_path.startswith("/") and len(db_path) > 2 and db_path[2] == ":":
            db_path = db_path[1:]
        db_file = Path(db_path)
        db_dir = db_file.parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If parsing or mkdir fails, let engine creation surface the original error.
        pass
    # SQLite-specific settings
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL settings
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize database - create tables if they don't exist."""
    # Ensure database directory exists for SQLite
    if is_sqlite:
        import os
        from pathlib import Path
        # Extract path from connection string
        db_url = settings.database_url
        if ":///" in db_url:
            db_path = db_url.split("://")[1].lstrip("/")
            # Handle Windows paths
            if not os.path.isabs(db_path) and db_path.startswith("/"):
                db_path = db_path[1:]
            db_dir = os.path.dirname(db_path) or "."
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        async with engine.begin() as conn:
            # Import all models to register them with Base
            from app.models import disruption, awb, flight, approval, audit
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


async def close_db():
    """Close database connections."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to get an async database session.
    Use this in tools and services that are not FastAPI endpoints.
    
    Usage:
        async with get_async_session() as db:
            result = await db.execute(query)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

