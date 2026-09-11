"""
LabelSure — Database Engine
Supports both SQLite (dev) and PostgreSQL (production) via env-driven DATABASE_URL.
Connection pooling is enabled automatically for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import get_settings

settings = get_settings()


from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Query parameters used by libpq (psycopg2 / psql) that cause TypeErrors in asyncpg.connect()
_LIBPQ_ONLY_PARAMS = {
    "channel_binding",
    "sslmode",
    "sslrootcert",
    "sslcert",
    "sslkey",
    "target_session_attrs",
    "gssencmode",
    "krbsrvname",
    "options",
    "service",
}


def _get_normalized_db_url(url: str) -> tuple[str, dict]:
    """Normalizes PostgreSQL & Neon connection strings for asyncpg.
    
    - Converts 'postgres://' or 'postgresql://' to 'postgresql+asyncpg://'
    - Filters out libpq-only query params (channel_binding, sslmode, etc.) which cause TypeErrors in asyncpg
    - Configures SSL via connect_args for cloud Postgres providers (Neon, Render, Supabase)
    """
    connect_args = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return url, connect_args

    # Normalize scheme for asyncpg
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Parse query string and filter libpq-only parameters
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    sslmode_val = qs.get("sslmode", [None])[0]
    has_ssl = (sslmode_val is not None and sslmode_val != "disable") or ("neon.tech" in url)

    if has_ssl:
        connect_args["ssl"] = "require"

    # Remove libpq-specific params to prevent asyncpg TypeError
    clean_qs = {k: v for k, v in qs.items() if k.lower() not in _LIBPQ_ONLY_PARAMS}
    clean_query = urlencode(clean_qs, doseq=True)

    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        clean_query,
        parsed.fragment,
    ))

    return clean_url, connect_args


def _build_engine():
    url, connect_args = _get_normalized_db_url(settings.database_url)

    # SQLite: no connection pooling, thread-safety override
    if settings.is_sqlite:
        return create_async_engine(
            url,
            echo=settings.debug,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

    # PostgreSQL / Neon (asyncpg): full connection pooling & SSL support
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        connect_args=connect_args,
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
