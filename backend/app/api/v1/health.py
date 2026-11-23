import asyncio
import time
from typing import Any
from fastapi import APIRouter, Response, status
from sqlalchemy import text
import redis.asyncio as aioredis
from app.core.config import get_settings
from app.db.session import engine
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("/live", summary="Liveness probe")
async def health_live() -> dict[str, str]:
    """Returns 200 if the FastAPI application process is up and running."""
    settings = get_settings()
    return {"status": "alive", "version": settings.APP_VERSION}


@router.get("/ready", summary="Readiness probe with deep dependency telemetry")
async def health_ready(response: Response) -> dict[str, Any]:
    """Runs concurrent checks on Postgres (+ pgvector extension), Redis, and Celery."""
    settings = get_settings()
    results: dict[str, Any] = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "components": {},
    }

    async def _check_postgres_inner() -> dict[str, Any]:
        async with engine.connect() as conn:
            # Verify basic query
            await conn.execute(text("SELECT 1"))
            # Verify pgvector extension
            ext_res = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            has_vector = ext_res.scalar_one_or_none() is not None
            if not has_vector:
                return {
                    "status": "unhealthy",
                    "error": "pgvector extension is missing",
                }
            return {"status": "healthy", "pgvector": True}

    async def check_postgres() -> dict[str, Any]:
        start = time.perf_counter()
        try:
            res = await asyncio.wait_for(_check_postgres_inner(), timeout=2.0)
            latency = round((time.perf_counter() - start) * 1000, 2)
            res["latency_ms"] = latency
            return res
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "unhealthy", "latency_ms": latency, "error": str(e)}

    async def _check_redis_inner() -> dict[str, Any]:
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
        await client.ping()
        await client.aclose()
        return {"status": "healthy"}

    async def check_redis() -> dict[str, Any]:
        start = time.perf_counter()
        try:
            res = await asyncio.wait_for(_check_redis_inner(), timeout=2.0)
            latency = round((time.perf_counter() - start) * 1000, 2)
            res["latency_ms"] = latency
            return res
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "unhealthy", "latency_ms": latency, "error": str(e)}

    def check_celery() -> dict[str, Any]:
        start = time.perf_counter()
        try:
            inspect = celery_app.control.inspect(timeout=1.0)
            ping_res = inspect.ping()
            latency = round((time.perf_counter() - start) * 1000, 2)
            if ping_res and len(ping_res) > 0:
                workers = list(ping_res.keys())
                return {"status": "healthy", "latency_ms": latency, "workers": workers}
            return {
                "status": "degraded",
                "latency_ms": latency,
                "message": "No active Celery workers responded",
            }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "degraded", "latency_ms": latency, "error": str(e)}

    # Run checks concurrently
    pg_task = asyncio.create_task(check_postgres())
    redis_task = asyncio.create_task(check_redis())
    celery_task = asyncio.to_thread(check_celery)

    pg_result, redis_result, celery_result = await asyncio.gather(
        pg_task, redis_task, celery_task
    )

    results["components"]["postgres"] = pg_result
    results["components"]["redis"] = redis_result
    results["components"]["celery"] = celery_result

    # Determine overall status
    is_pg_unhealthy = pg_result["status"] == "unhealthy"
    is_redis_unhealthy = redis_result["status"] == "unhealthy"
    is_celery_unhealthy = celery_result["status"] == "unhealthy"

    if is_pg_unhealthy or is_redis_unhealthy:
        results["status"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif is_celery_unhealthy or celery_result["status"] == "degraded":
        results["status"] = "degraded"
        response.status_code = status.HTTP_200_OK
    else:
        results["status"] = "healthy"
        response.status_code = status.HTTP_200_OK

    return results
