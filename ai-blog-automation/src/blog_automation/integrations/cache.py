"""Caching layer for API responses.

Provides in-memory and optional persistent caching for API responses
to reduce API calls and costs.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Manages caching of API responses.

    Supports both in-memory caching and optional file-based persistence.
    Different TTLs can be configured for different types of data.
    """

    # Default TTLs in seconds
    DEFAULT_TTLS = {
        "keyword_volume": 30 * 24 * 3600,  # 30 days
        "keyword_difficulty": 30 * 24 * 3600,  # 30 days
        "serp_features": 7 * 24 * 3600,  # 7 days
        "top_pages": 3 * 24 * 3600,  # 3 days
        "search_results": 24 * 3600,  # 1 day
        "default": 3600,  # 1 hour
    }

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        persist: bool = False,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for persistent cache
            persist: Whether to persist cache to disk
        """
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self.persist = persist
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".cache")

        if persist:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from arguments.

        Args:
            prefix: Key prefix (e.g., "ahrefs_volume")
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{prefix}:{key_hash}"

    def get_cached(
        self,
        key: str,
        cache_type: str = "default",
    ) -> Any | None:
        """Get a cached value.

        Args:
            key: Cache key
            cache_type: Type of cache (for TTL lookup)

        Returns:
            Cached value or None if not found/expired
        """
        # Check memory cache
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            ttl = self.DEFAULT_TTLS.get(cache_type, self.DEFAULT_TTLS["default"])

            if time.time() - entry["timestamp"] < ttl:
                logger.debug(f"Cache hit (memory): {key}")
                return entry["value"]
            else:
                # Expired
                del self._memory_cache[key]

        # Check file cache
        if self.persist:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file) as f:
                        entry = json.load(f)

                    ttl = self.DEFAULT_TTLS.get(
                        cache_type, self.DEFAULT_TTLS["default"]
                    )
                    if time.time() - entry["timestamp"] < ttl:
                        # Load into memory cache
                        self._memory_cache[key] = entry
                        logger.debug(f"Cache hit (file): {key}")
                        return entry["value"]
                    else:
                        # Expired, remove file
                        cache_file.unlink()
                except (json.JSONDecodeError, KeyError):
                    cache_file.unlink()

        return None

    def set_cache(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
    ) -> None:
        """Set a cached value.

        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache (for TTL lookup)
        """
        entry = {
            "value": value,
            "timestamp": time.time(),
            "type": cache_type,
        }

        # Store in memory
        self._memory_cache[key] = entry

        # Persist to file
        if self.persist:
            cache_file = self.cache_dir / f"{key}.json"
            try:
                with open(cache_file, "w") as f:
                    json.dump(entry, f)
                logger.debug(f"Cache set: {key}")
            except (TypeError, IOError) as e:
                logger.warning(f"Failed to persist cache: {e}")

    def clear_cache(self, prefix: str | None = None) -> int:
        """Clear cached values.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Number of entries cleared
        """
        count = 0

        # Clear memory cache
        if prefix:
            keys_to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._memory_cache[key]
                count += 1
        else:
            count = len(self._memory_cache)
            self._memory_cache.clear()

        # Clear file cache
        if self.persist:
            for cache_file in self.cache_dir.glob("*.json"):
                if prefix is None or cache_file.stem.startswith(prefix):
                    cache_file.unlink()
                    count += 1

        logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        memory_count = len(self._memory_cache)
        file_count = 0

        if self.persist:
            file_count = len(list(self.cache_dir.glob("*.json")))

        return {
            "memory_entries": memory_count,
            "file_entries": file_count,
            "persist_enabled": self.persist,
            "cache_dir": str(self.cache_dir),
        }


def cached(
    cache_type: str = "default",
    key_prefix: str | None = None,
) -> Callable:
    """Decorator for caching function results.

    Args:
        cache_type: Type of cache (for TTL)
        key_prefix: Optional key prefix

    Returns:
        Decorated function

    Example:
        @cached(cache_type="keyword_volume", key_prefix="ahrefs")
        def get_search_volume(keyword: str) -> int:
            ...
    """
    # Global cache instance
    _cache = CacheManager()

    def decorator(func: Callable) -> Callable:
        prefix = key_prefix or func.__name__

        def wrapper(*args, **kwargs):
            key = _cache._generate_key(prefix, *args, **kwargs)

            # Check cache
            cached_value = _cache.get_cached(key, cache_type)
            if cached_value is not None:
                return cached_value

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            _cache.set_cache(key, result, cache_type)

            return result

        return wrapper

    return decorator


# Global cache instance
_global_cache: CacheManager | None = None


def get_cache() -> CacheManager:
    """Get the global cache instance.

    Returns:
        CacheManager instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache
