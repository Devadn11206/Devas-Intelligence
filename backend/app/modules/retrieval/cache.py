import hashlib
import json
import logging
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Fallback in-memory cache if Redis is unavailable
_memory_cache: dict[str, str] = {}
_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
    except Exception as e:
        logger.warning("Could not initialize redis client: %s. Using fakeredis/memory.", e)
        try:
            import fakeredis.aioredis
            _redis_client = fakeredis.aioredis.FakeRedis()
        except Exception:
            _redis_client = None
    return _redis_client


class SearchCache:
    """Provides caching for search queries with automatic fallback to fake/memory."""

    @staticmethod
    def generate_cache_key(canonical_query_str: str) -> str:
        h = hashlib.sha256(canonical_query_str.encode("utf-8")).hexdigest()
        return f"search:cache:{h}"

    @classmethod
    async def get(cls, key: str) -> Optional[dict]:
        client = get_redis_client()
        if client:
            try:
                raw = await client.get(key)
                if raw:
                    return json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
            except Exception as e:
                logger.debug("Redis cache get error: %s", e)
        # Check in-memory fallback
        raw = _memory_cache.get(key)
        if raw:
            return json.loads(raw)
        return None

    @classmethod
    async def set(cls, key: str, data: dict, ttl: int = 300) -> None:
        val = json.dumps(data, default=str)
        client = get_redis_client()
        if client:
            try:
                await client.set(key, val, ex=ttl)
                return
            except Exception as e:
                logger.debug("Redis cache set error: %s", e)
        _memory_cache[key] = val
