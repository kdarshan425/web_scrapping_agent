"""Async SQLAlchemy engine + session factory (PostgreSQL)."""
from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_VALID_SSL_MODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}


def _clean(value) -> str:
    """Remove stray spaces / quotes that often sneak into .env values."""
    if isinstance(value, (tuple, list)):
        value = value[-1]
    return str(value).strip().strip("\"'").strip().lower()


def build_engine(raw_url: str):
    """Create the engine from DATABASE_URL, tolerating Neon / Supabase style URLs."""
    url = make_url(raw_url.strip().strip("\"'"))
    query = dict(url.query)

    ssl_mode = None
    for key in ("sslmode", "ssl"):
        if key in query:
            ssl_mode = _clean(query.pop(key))
    query.pop("channel_binding", None)
    url = url.set(query=query)

    connect_args: dict = {}
    if ssl_mode in _VALID_SSL_MODES - {"disable"}:
        connect_args["ssl"] = ssl_mode
    elif ssl_mode in {"true", "1", "yes"}:
        connect_args["ssl"] = "require"
    elif ssl_mode is None and url.host and url.host not in {"localhost", "127.0.0.1", "postgres"}:
        connect_args["ssl"] = "require"

    # Supabase/Neon pooler endpoints do not support prepared-statement caching
    if url.host and ("pooler" in url.host or url.port == 6543):
        connect_args["statement_cache_size"] = 0

    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = build_engine(get_settings().database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class of every ORM model."""


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)