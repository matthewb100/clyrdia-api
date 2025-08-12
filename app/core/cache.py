"""
Caching utilities with Redis backend
"""
import json
import hashlib
from typing import Any, Optional, Union
import redis.asyncio as redis
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class CacheManager:
    """Redis-based cache manager"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = settings.cache_ttl
        self.max_size = settings.cache_max_size
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis cache")
    
    def _generate_key(self, key: str) -> str:
        """Generate a consistent cache key"""
        return f"clyrdia:{hashlib.md5(key.encode()).hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_key(key)
            value = await self.redis_client.get(cache_key)
            
            if value:
                return json.loads(value)
            
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            ttl = ttl or self.default_ttl
            
            # Check cache size limit
            if await self._check_size_limit():
                await self._evict_oldest()
            
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(value, default=str)
            )
            
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            result = await self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            return await self.redis_client.exists(cache_key) > 0
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value in cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_key(key)
            return await self.redis_client.incr(cache_key, amount)
        except Exception as e:
            logger.error("Cache increment error", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for a key"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_key(key)
            return await self.redis_client.expire(cache_key, ttl)
        except Exception as e:
            logger.error("Cache expire error", key=key, error=str(e))
            return False
    
    async def _check_size_limit(self) -> bool:
        """Check if cache size exceeds limit"""
        if not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys("clyrdia:*")
            return len(keys) >= self.max_size
        except Exception:
            return False
    
    async def _evict_oldest(self):
        """Evict oldest cache entries"""
        if not self.redis_client:
            return
        
        try:
            # Get all keys with their TTL
            keys = await self.redis_client.keys("clyrdia:*")
            if not keys:
                return
            
            # Get TTL for each key
            key_ttls = []
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:  # Only consider keys with TTL
                    key_ttls.append((key, ttl))
            
            # Sort by TTL (ascending) and remove oldest 10%
            key_ttls.sort(key=lambda x: x[1])
            to_remove = max(1, len(key_ttls) // 10)
            
            for key, _ in key_ttls[:to_remove]:
                await self.redis_client.delete(key)
            
            logger.info("Evicted old cache entries", count=to_remove)
        except Exception as e:
            logger.error("Cache eviction error", error=str(e))
    
    async def clear_all(self) -> bool:
        """Clear all cache entries"""
        if not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys("clyrdia:*")
            if keys:
                await self.redis_client.delete(*keys)
                logger.info("Cleared all cache entries", count=len(keys))
            return True
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return False


# Global cache instance
cache = CacheManager()


async def get_cached_or_fetch(
    key: str,
    fetch_func,
    ttl: Optional[int] = None,
    *args,
    **kwargs
) -> Any:
    """Get value from cache or fetch using provided function"""
    # Try to get from cache first
    cached_value = await cache.get(key)
    if cached_value is not None:
        logger.debug("Cache hit", key=key)
        return cached_value
    
    # Fetch fresh value
    logger.debug("Cache miss", key=key)
    fresh_value = await fetch_func(*args, **kwargs)
    
    # Cache the fresh value
    if fresh_value is not None:
        await cache.set(key, fresh_value, ttl)
    
    return fresh_value 