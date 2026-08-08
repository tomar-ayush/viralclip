from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.common.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,      # test connection before use
    pool_size=5,             # BUG-2 fix: Neon pooler max = 10; keep low
    max_overflow=5,          # BUG-2 fix: total max 10 connections
    pool_recycle=300,        # BUG-9 fix: recycle before Neon's 5min idle timeout
    connect_args={
        "server_settings": {"timezone": "UTC"}  # fix: asyncpg rejects tz-aware datetimes on TIMESTAMP columns
    },
)


AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
