from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
    "pool_pre_ping": settings.environment != "test",
}
if settings.environment == "test":
    # Pytest creates isolated event loops for async tests. NullPool prevents an
    # asyncpg connection created on one loop from being reused by another.
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
