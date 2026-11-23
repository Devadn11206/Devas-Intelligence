from collections.abc import AsyncGenerator
import uuid
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
    "echo": False,
    "future": True,
}
if settings.TESTING:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_db_current_user_id(session: AsyncSession, user_id: uuid.UUID | str | None) -> None:
    """Sets PostgreSQL session variable `app.current_user_id` inside transaction for Row-Level Security."""
    if user_id is not None:
        val = str(user_id)
        # Using set_config(setting, value, is_local) -> true makes it local to current transaction
        await session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": val},
        )
    else:
        await session.execute(
            text("SELECT set_config('app.current_user_id', '', true)")
        )
