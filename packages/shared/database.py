"""Database session management with SQLAlchemy Async Engine."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from packages.shared.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_async_database_url(url_str: str) -> tuple[str, dict[str, Any]]:
    """
    Normalizes database URLs provided by cloud hosts (Render, Heroku, Supabase, Neon)
    for SQLAlchemy AsyncEngine with asyncpg driver.
    
    1. Replaces 'postgres://' or 'postgresql://' with 'postgresql+asyncpg://'.
    2. Strips 'sslmode' query parameter (which asyncpg rejects as an unrecognized argument)
       and translates it into connect_args={'ssl': ssl_context or bool}.
    """
    parts = urlsplit(url_str)
    scheme = parts.scheme

    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    elif scheme == "postgresql+psycopg2":
        scheme = "postgresql+asyncpg"

    query_params = dict(parse_qsl(parts.query, keep_blank_values=True))
    connect_args: dict[str, Any] = {}

    ssl_mode = query_params.pop("sslmode", None)
    if ssl_mode in ("require", "verify-ca", "verify-full", "prefer"):
        # For cloud providers with self-signed intermediate certificates (like Render internal/external)
        # asyncpg accepts ssl=True or an SSLContext instance.
        connect_args["ssl"] = True
    elif "ssl" in query_params:
        val = query_params.pop("ssl").lower()
        if val in ("true", "1", "require"):
            connect_args["ssl"] = True

    new_query = urlencode(query_params)
    normalized_url = urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))

    return normalized_url, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        clean_url, connect_args = normalize_async_database_url(settings.DATABASE_URL)
        _engine = create_async_engine(
            clean_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
        )
    return _engine


async def dispose_engine() -> None:
    """Explicitly clean up connection pool across event loops."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_factory()
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
