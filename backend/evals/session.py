"""Dedicated database session for Evaluation benchmarks.
Pins all evals exclusively to the `deva_test` database to protect production `deva_db`.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import get_settings

settings = get_settings()

# Always force deva_test database
base_url = settings.DATABASE_URL
if "/deva_db" in base_url:
    eval_db_url = base_url.replace("/deva_db", "/deva_test")
elif not base_url.endswith("/deva_test"):
    # Split by / and replace database name
    parts = base_url.rsplit("/", 1)
    eval_db_url = f"{parts[0]}/deva_test"
else:
    eval_db_url = base_url

eval_engine = create_async_engine(
    eval_db_url,
    echo=False,
    future=True,
    poolclass=NullPool,
)

eval_async_session_factory = async_sessionmaker(
    bind=eval_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
