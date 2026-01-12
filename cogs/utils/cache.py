import asyncio
import time
import sys
from typing import Any, Optional
from collections import defaultdict

class TTLCache:
    """
    Thread-safe Time-To-Live based cache for reducing redundant API calls.
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache = {}  # key -> (value, expiration_time)
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        # Enhanced tracking
        self._key_hits = defaultdict(int)  # Track hits per key prefix
        self._key_access_times = []  # Track recent access times (last 100)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value if it exists and hasn't expired.
        Returns None if key doesn't exist or has expired.
        """
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            value, expiration = self._cache[key]
            
            # Check if expired
            if time.time() > expiration:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            
            # Track per-key-prefix hits
            key_prefix = key.split(':')[0] if ':' in key else key
            self._key_hits[key_prefix] += 1
            
            # Track access time
            self._key_access_times.append(time.time())
            if len(self._key_access_times) > 100:
                self._key_access_times.pop(0)
            
            return value
    
    async def set(self, key: str, value: Any, ttl: int):
        """
        Store a value in cache with a time-to-live in seconds.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        async with self._lock:
            # Auto-cleanup if cache is too large
            if len(self._cache) >= self._max_size:
                await self._cleanup()
            
            expiration = time.time() + ttl
            self._cache[key] = (value, expiration)
    
    async def clear(self):
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._key_hits.clear()
            self._key_access_times.clear()
    
    async def _cleanup(self):
        """Remove expired entries. Called automatically when cache is full."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired_keys:
            del self._cache[k]
        
        # If still too large after cleanup, remove oldest entries
        if len(self._cache) >= self._max_size:
            # Sort by expiration time and remove oldest 20%
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            remove_count = self._max_size // 5
            for k, _ in sorted_items[:remove_count]:
                del self._cache[k]
    
    def get_stats(self) -> dict:
        """Get basic cache statistics (thread-safe)."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self._cache)
        }
    
    async def get_detailed_stats(self) -> dict:
        """
        Get detailed cache statistics including per-endpoint breakdown.
        Thread-safe and optimized for performance.
        """
        async with self._lock:
            # Get basic stats
            basic = self.get_stats()
            
            # Calculate memory usage (optimized - sample only if too large)
            cache_size = len(self._cache)
            if cache_size > 100:
                # Sample-based estimation for large caches
                sample_keys = list(self._cache.keys())[:50]
                sample_bytes = sum(
                    sys.getsizeof(k) + sys.getsizeof(self._cache[k][0]) 
                    for k in sample_keys
                )
                # Extrapolate
                memory_bytes = (sample_bytes / 50) * cache_size + sys.getsizeof(self._cache)
            else:
                # Full calculation for small caches
                memory_bytes = sys.getsizeof(self._cache)
                for key, (value, _) in self._cache.items():
                    memory_bytes += sys.getsizeof(key) + sys.getsizeof(value)
            
            memory_mb = memory_bytes / (1024 * 1024)
            
            # Top 5 most hit endpoints (already sorted dict)
            top_keys = sorted(self._key_hits.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Recent activity (requests per minute estimate)
            rpm = 0
            if len(self._key_access_times) >= 2:
                time_span = self._key_access_times[-1] - self._key_access_times[0]
                if time_span > 0:
                    rpm = (len(self._key_access_times) / time_span) * 60
            
            return {
                **basic,
                "memory_mb": round(memory_mb, 2),
                "max_size": self._max_size,
                "utilization": f"{(cache_size / self._max_size * 100):.1f}%",
                "top_endpoints": top_keys,
                "requests_per_minute": round(rpm, 1)
            }


