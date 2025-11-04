"""
Template for generating caching middleware for MCP servers.
"""


def generate_cache_middleware() -> str:
    """Generate the cache middleware module code."""
    return '''"""
Response caching middleware for MCP server.

This module provides caching capabilities for expensive tool operations:
- Configurable TTL (time-to-live) for cache entries
- Cache key generation from tool name, path, params, and body
- Decorator for tool functions to enable caching
- Storage backend integration (uses pluggable storage)

⚡ FastMCP 2.13+ Built-in Caching (Recommended):
----------------------------------------------------
FastMCP 2.13+ includes ResponseCachingMiddleware with advanced features:
- Caches tool calls, resource reads, and prompts
- Built-in statistics and monitoring
- Size limits and automatic eviction
- py-key-value-aio backend support (Redis, DynamoDB, Disk, Memory, etc.)

To use FastMCP's built-in caching, add it to your server:

    from fastmcp.server.middleware.caching import ResponseCachingMiddleware
    from key_value.aio.stores.disk import DiskStore

    # In your main server file, before app.run():
    app.add_middleware(ResponseCachingMiddleware(
        cache_storage=DiskStore(directory="cache"),
        list_tools_settings={"ttl": 300},      # 5 minutes
        call_tool_settings={"ttl": 3600},       # 1 hour
        read_resource_settings={"ttl": 3600}    # 1 hour
    ))

See: https://docs.fastmcp.com/servers/middleware/#caching-middleware

📦 This Module - Decorator-Based Caching:
------------------------------------------
This file provides a decorator-based caching utility for individual functions.
Use @cache.cached(ttl=600) to cache expensive function results.

Usage:
    from storage import get_storage
    from cache import get_cache_middleware

    storage = get_storage("filesystem")
    cache = get_cache_middleware(storage, default_ttl=300)

    @cache.cached(ttl=600)
    async def expensive_tool(param: str) -> dict:
        # ... expensive operation ...
        return result
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Optional, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


class CacheMiddleware:
    """
    Decorator-based cache for function responses.

    Provides TTL-based caching with storage backend integration.
    Use this to cache expensive function results with @cache.cached(ttl=600).

    Note: This is different from FastMCP's ResponseCachingMiddleware,
    which automatically caches MCP protocol responses at the middleware level.
    """

    def __init__(self, storage, default_ttl: int = 300):
        """
        Initialize cache middleware.

        Args:
            storage: StorageBackend instance for persistence
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.storage = storage
        self.default_ttl = default_ttl
        logger.info(f"Initialized cache middleware with {default_ttl}s default TTL")

    def _generate_cache_key(self, tool_name: str, *args, **kwargs) -> str:
        """
        Generate a unique cache key from tool name and arguments.

        Args:
            tool_name: Name of the tool being cached
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Unique cache key string
        """
        # Create deterministic representation of arguments
        key_parts = [tool_name]

        if args:
            key_parts.append(json.dumps(args, sort_keys=True, default=str))

        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True, default=str))

        key_string = "|".join(key_parts)

        # Use hash for consistent key length
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"cache:{tool_name}:{key_hash}"

    async def get(self, tool_name: str, *args, **kwargs) -> Optional[Any]:
        """
        Retrieve cached tool response.

        Args:
            tool_name: Name of the tool
            *args: Positional arguments passed to tool
            **kwargs: Keyword arguments passed to tool

        Returns:
            Cached response data or None if not found/expired
        """
        cache_key = self._generate_cache_key(tool_name, *args, **kwargs)

        try:
            cached = await self.storage.get(cache_key)
            if not cached:
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(cached['expires_at'])
            if expires_at < datetime.now(timezone.utc):
                logger.debug(f"Cache expired for {tool_name}")
                await self.storage.delete(cache_key)
                return None

            logger.debug(f"Cache hit for {tool_name}")
            return cached['data']

        except Exception as e:
            logger.warning(f"Cache get failed for {tool_name}: {e}")
            return None

    async def set(self, tool_name: str, data: Any, ttl: Optional[int] = None,
                  *args, **kwargs) -> bool:
        """
        Cache a tool response.

        Args:
            tool_name: Name of the tool
            data: Response data to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
            *args: Positional arguments that were passed to tool
            **kwargs: Keyword arguments that were passed to tool

        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self._generate_cache_key(tool_name, *args, **kwargs)
        ttl = ttl if ttl is not None else self.default_ttl

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        cache_entry = {
            'data': data,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': expires_at.isoformat(),
            'ttl': ttl
        }

        try:
            await self.storage.set(cache_key, cache_entry)
            logger.debug(f"Cached {tool_name} for {ttl}s")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {tool_name}: {e}")
            return False

    async def invalidate(self, tool_name: str, *args, **kwargs) -> bool:
        """
        Invalidate a specific cached response.

        Args:
            tool_name: Name of the tool
            *args: Positional arguments passed to tool
            **kwargs: Keyword arguments passed to tool

        Returns:
            True if cache entry was deleted, False otherwise
        """
        cache_key = self._generate_cache_key(tool_name, *args, **kwargs)

        try:
            await self.storage.delete(cache_key)
            logger.debug(f"Invalidated cache for {tool_name}")
            return True
        except Exception as e:
            logger.warning(f"Cache invalidation failed for {tool_name}: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cached responses.

        Returns:
            True if cache was cleared, False otherwise
        """
        try:
            # Note: This clears ALL storage, not just cache entries
            # In production, you might want to iterate and delete only cache:* keys
            await self.storage.clear()
            logger.info("Cleared all cache entries")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False

    def cached(self, ttl: Optional[int] = None):
        """
        Decorator to cache tool responses.

        Args:
            ttl: Time-to-live in seconds (uses default_ttl if None)

        Example:
            @cache_middleware.cached(ttl=600)
            async def expensive_tool(param: str) -> dict:
                # ... expensive operation ...
                return result
        """
        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                tool_name = func.__name__

                # Try to get from cache
                cached_result = await self.get(tool_name, *args, **kwargs)
                if cached_result is not None:
                    return cached_result

                # Execute function
                result = await func(*args, **kwargs)

                # Cache the result
                await self.set(tool_name, result, ttl, *args, **kwargs)

                return result

            return wrapper
        return decorator


def get_cache_middleware(storage, default_ttl: int = 300):
    """
    Factory function to create cache middleware instance.

    Args:
        storage: StorageBackend instance
        default_ttl: Default TTL in seconds (default: 5 minutes)

    Returns:
        CacheMiddleware instance with decorator support

    Example:
        from storage import get_storage
        from cache import get_cache_middleware

        storage = get_storage("filesystem")
        cache = get_cache_middleware(storage, default_ttl=600)

        @cache.cached(ttl=300)
        async def my_tool(param: str) -> dict:
            return {"result": "expensive computation"}
    """
    return CacheMiddleware(storage, default_ttl)
'''
