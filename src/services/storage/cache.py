"""Cache service using Redis."""

import json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from loguru import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class InMemoryCache:
    """Simple in-memory cache for development/fallback."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        import time
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._cache[key]
            del self._expiry[key]
            return None
        return self._cache.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        import time
        self._cache[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        """Check if key exists."""
        import time
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._cache[key]
            del self._expiry[key]
            return 0
        return 1 if key in self._cache else 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        import fnmatch
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key."""
        import time
        if key in self._cache:
            self._expiry[key] = time.time() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        """Get TTL of key."""
        import time
        if key not in self._cache:
            return -2
        if key not in self._expiry:
            return -1
        remaining = int(self._expiry[key] - time.time())
        return max(0, remaining)

    async def incr(self, key: str) -> int:
        """Increment value."""
        val = int(self._cache.get(key, 0)) + 1
        self._cache[key] = str(val)
        return val

    async def lpush(self, key: str, *values: str) -> int:
        """Push to list."""
        if key not in self._cache:
            self._cache[key] = []
        for v in values:
            self._cache[key].insert(0, v)
        return len(self._cache[key])

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list."""
        if key not in self._cache:
            return []
        lst = self._cache[key]
        if end == -1:
            end = len(lst)
        else:
            end = end + 1
        return lst[start:end]

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list."""
        if key not in self._cache:
            return True
        lst = self._cache[key]
        if end == -1:
            end = len(lst)
        else:
            end = end + 1
        self._cache[key] = lst[start:end]
        return True

    async def close(self) -> None:
        """Close cache (no-op for in-memory)."""
        self._cache.clear()
        self._expiry.clear()


class CacheService:
    """Cache service with Redis backend and in-memory fallback."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_password: Optional[str] = None,
        prefix: str = "aigf:",
    ):
        """Initialize cache service.

        Args:
            redis_url: Redis connection URL
            redis_password: Redis password
            prefix: Key prefix for all cache keys
        """
        self.prefix = prefix
        self.redis_url = redis_url
        self.redis_password = redis_password
        self._client: Optional[Union[aioredis.Redis, InMemoryCache]] = None
        self._use_redis = REDIS_AVAILABLE and redis_url is not None

    async def connect(self) -> None:
        """Connect to cache backend."""
        if self._use_redis:
            try:
                self._client = aioredis.from_url(
                    self.redis_url,
                    password=self.redis_password,
                    decode_responses=True,
                )
                await self._client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
                self._client = InMemoryCache()
                self._use_redis = False
        else:
            self._client = InMemoryCache()
            logger.info("Using in-memory cache")

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get string value from cache."""
        if not self._client:
            await self.connect()
        return await self._client.get(self._make_key(key))

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set string value in cache."""
        if not self._client:
            await self.connect()
        return await self._client.set(self._make_key(key), value, ex=ttl)

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set JSON value in cache."""
        return await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        if not self._client:
            await self.connect()
        return await self._client.delete(self._make_key(key))

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            await self.connect()
        return bool(await self._client.exists(self._make_key(key)))

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key."""
        if not self._client:
            await self.connect()
        return await self._client.expire(self._make_key(key), seconds)

    async def ttl(self, key: str) -> int:
        """Get TTL of key."""
        if not self._client:
            await self.connect()
        return await self._client.ttl(self._make_key(key))

    async def incr(self, key: str) -> int:
        """Increment counter."""
        if not self._client:
            await self.connect()
        return await self._client.incr(self._make_key(key))

    # List operations for conversation history
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to list."""
        if not self._client:
            await self.connect()
        return await self._client.lpush(self._make_key(key), *values)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list."""
        if not self._client:
            await self.connect()
        return await self._client.lrange(self._make_key(key), start, end)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list to range."""
        if not self._client:
            await self.connect()
        return await self._client.ltrim(self._make_key(key), start, end)

    # Convenience methods for common patterns
    async def get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user conversation context."""
        return await self.get_json(f"user:{user_id}:context")

    async def set_user_context(
        self,
        user_id: int,
        context: Dict[str, Any],
        ttl: int = 3600,
    ) -> bool:
        """Set user conversation context."""
        return await self.set_json(f"user:{user_id}:context", context, ttl)

    async def get_rate_limit(self, user_id: int, window: str) -> int:
        """Get rate limit counter for user."""
        value = await self.get(f"rate:{user_id}:{window}")
        return int(value) if value else 0

    async def incr_rate_limit(self, user_id: int, window: str, ttl: int) -> int:
        """Increment rate limit counter."""
        key = f"rate:{user_id}:{window}"
        count = await self.incr(key)
        if count == 1:
            await self.expire(key, ttl)
        return count

    async def close(self) -> None:
        """Close cache connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Cache connection closed")


# Global cache instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        raise RuntimeError("Cache service not initialized. Call init_cache() first.")
    return _cache_service


async def init_cache(
    redis_url: Optional[str] = None,
    redis_password: Optional[str] = None,
) -> CacheService:
    """Initialize the global cache service."""
    global _cache_service
    _cache_service = CacheService(redis_url, redis_password)
    await _cache_service.connect()
    return _cache_service


async def close_cache() -> None:
    """Close the global cache service."""
    global _cache_service
    if _cache_service:
        await _cache_service.close()
        _cache_service = None
