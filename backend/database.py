"""
LabelSure — Database Engine
Supports both SQLite (dev) and PostgreSQL (production) via env-driven DATABASE_URL.
Connection pooling is enabled automatically for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import get_settings

settings = get_settings()


def _build_engine():
    url = settings.database_url

    # SQLite: no connection pooling, thread-safety override
    if settings.is_sqlite:
        return create_async_engine(
            url,
            echo=settings.debug,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL (asyncpg): full connection pooling
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables on startup.
    In production, prefer Alembic migrations over auto-create.
    """
    async with engine.begin() as conn:
        from backend import models  # noqa: F401 – registers all models with Base
        await conn.run_sync(Base.metadata.create_all)
