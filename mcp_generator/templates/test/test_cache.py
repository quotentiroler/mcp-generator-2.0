"""
Template for generating cache middleware tests.
"""


def generate_cache_tests() -> str:
    """Generate comprehensive tests for cache middleware."""
    return '''"""
Tests for cache middleware functionality.

Tests cover:
- Cache hit/miss behavior
- TTL expiration
- Cache key generation
- Decorator usage
- Cache invalidation
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generated_mcp"))

try:
    from storage import get_storage
    from cache import get_cache_middleware
except ImportError:
    print("⚠️  Skipped: Cache and storage modules not generated")
    print("   Run with: uv run generate-mcp --enable-storage --enable-caching")
    sys.exit(0)


async def test_cache_hit_miss():
    """Test basic cache hit and miss behavior."""
    print("\\n🧪 Testing Cache Hit/Miss...")

    # Use in-memory storage for tests
    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=300)

    tool_name = "test_tool"
    test_data = {"result": "expensive computation"}

    # First call should be a cache miss
    cached = await cache.get(tool_name, arg1="value1", arg2="value2")
    assert cached is None, "❌ Expected cache miss on first call"
    print("   ✅ Cache miss on first call")

    # Set cache
    success = await cache.set(tool_name, test_data, None, arg1="value1", arg2="value2")
    assert success, "❌ Failed to set cache"
    print("   ✅ Cache set successfully")

    # Second call should be a cache hit
    cached = await cache.get(tool_name, arg1="value1", arg2="value2")
    assert cached == test_data, "❌ Expected cache hit with matching data"
    print("   ✅ Cache hit with correct data")

    # Different args should be a cache miss
    cached = await cache.get(tool_name, arg1="different", arg2="values")
    assert cached is None, "❌ Expected cache miss with different args"
    print("   ✅ Cache miss with different args")


async def test_cache_ttl_expiration():
    """Test that cache entries expire based on TTL."""
    print("\\n🧪 Testing Cache TTL Expiration...")

    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=1)  # 1 second TTL

    tool_name = "expiring_tool"
    test_data = {"result": "will expire"}

    # Set cache with 1 second TTL
    await cache.set(tool_name, test_data, 1, arg="test")
    print("   ✅ Cache entry created with 1s TTL")

    # Should hit immediately
    cached = await cache.get(tool_name, arg="test")
    assert cached == test_data, "❌ Expected cache hit immediately"
    print("   ✅ Cache hit before expiration")

    # Wait for expiration
    print("   ⏳ Waiting 1.5 seconds for expiration...")
    await asyncio.sleep(1.5)

    # Should miss after expiration
    cached = await cache.get(tool_name, arg="test")
    assert cached is None, "❌ Expected cache miss after TTL expiration"
    print("   ✅ Cache miss after TTL expiration")


async def test_cache_key_generation():
    """Test that cache keys are generated consistently and uniquely."""
    print("\\n🧪 Testing Cache Key Generation...")

    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=300)

    # Same args should generate same key
    key1 = cache._generate_cache_key("tool", "arg1", "arg2", kwarg="value")
    key2 = cache._generate_cache_key("tool", "arg1", "arg2", kwarg="value")
    assert key1 == key2, "❌ Same args should generate same cache key"
    print("   ✅ Consistent key generation for same args")

    # Different args should generate different keys
    key3 = cache._generate_cache_key("tool", "different", "args")
    assert key1 != key3, "❌ Different args should generate different keys"
    print("   ✅ Different keys for different args")

    # Different tool names should generate different keys
    key4 = cache._generate_cache_key("other_tool", "arg1", "arg2", kwarg="value")
    assert key1 != key4, "❌ Different tools should generate different keys"
    print("   ✅ Different keys for different tool names")

    # Arg order matters for positional args
    key5 = cache._generate_cache_key("tool", "arg2", "arg1", kwarg="value")
    assert key1 != key5, "❌ Arg order should affect cache key"
    print("   ✅ Positional arg order affects cache key")


async def test_cache_decorator():
    """Test the @cached decorator functionality."""
    print("\\n🧪 Testing Cache Decorator...")

    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=300)

    # Track how many times function is called
    call_count = {"count": 0}

    @cache.cached(ttl=10)
    async def expensive_function(x: int, y: int) -> dict:
        """Simulate an expensive operation."""
        call_count["count"] += 1
        await asyncio.sleep(0.01)  # Simulate work
        return {"result": x + y, "computed": True}

    # First call should execute the function
    result1 = await expensive_function(5, 3)
    assert result1 == {"result": 8, "computed": True}, "❌ Wrong result"
    assert call_count["count"] == 1, "❌ Function should be called once"
    print("   ✅ First call executes function")

    # Second call with same args should use cache
    result2 = await expensive_function(5, 3)
    assert result2 == {"result": 8, "computed": True}, "❌ Cached result mismatch"
    assert call_count["count"] == 1, "❌ Function should not be called again"
    print("   ✅ Second call uses cache (function not executed)")

    # Different args should execute function again
    result3 = await expensive_function(10, 20)
    assert result3 == {"result": 30, "computed": True}, "❌ Wrong result"
    assert call_count["count"] == 2, "❌ Function should be called for different args"
    print("   ✅ Different args execute function")


async def test_cache_invalidation():
    """Test cache invalidation."""
    print("\\n🧪 Testing Cache Invalidation...")

    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=300)

    tool_name = "invalidate_test"
    test_data = {"result": "data"}

    # Set cache
    await cache.set(tool_name, test_data, None, arg="value")
    cached = await cache.get(tool_name, arg="value")
    assert cached == test_data, "❌ Cache should be set"
    print("   ✅ Cache entry created")

    # Invalidate specific entry
    success = await cache.invalidate(tool_name, arg="value")
    assert success, "❌ Invalidation should succeed"
    print("   ✅ Cache invalidated")

    # Should be a miss now
    cached = await cache.get(tool_name, arg="value")
    assert cached is None, "❌ Cache should be invalidated"
    print("   ✅ Cache miss after invalidation")


async def test_cache_clear_all():
    """Test clearing all cached entries."""
    print("\\n🧪 Testing Cache Clear All...")

    storage = get_storage("memory")
    cache = get_cache_middleware(storage, default_ttl=300)

    # Set multiple cache entries
    await cache.set("tool1", {"data": 1}, None, arg="a")
    await cache.set("tool2", {"data": 2}, None, arg="b")
    await cache.set("tool3", {"data": 3}, None, arg="c")
    print("   ✅ Created 3 cache entries")

    # Verify they exist
    assert await cache.get("tool1", arg="a") is not None
    assert await cache.get("tool2", arg="b") is not None
    assert await cache.get("tool3", arg="c") is not None
    print("   ✅ All entries accessible")

    # Clear all
    success = await cache.clear_all()
    assert success, "❌ Clear all should succeed"
    print("   ✅ Cache cleared")

    # All should be misses now
    assert await cache.get("tool1", arg="a") is None
    assert await cache.get("tool2", arg="b") is None
    assert await cache.get("tool3", arg="c") is None
    print("   ✅ All entries removed")


async def test_cache_with_filesystem_storage():
    """Test cache with filesystem storage backend."""
    print("\\n🧪 Testing Cache with Filesystem Storage...")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = get_storage("filesystem", base_dir=tmpdir)
        cache = get_cache_middleware(storage, default_ttl=300)

        tool_name = "fs_test"
        test_data = {"result": "filesystem data"}

        # Set cache
        await cache.set(tool_name, test_data, None, arg="test")
        print("   ✅ Cache stored to filesystem")

        # Get cache
        cached = await cache.get(tool_name, arg="test")
        assert cached == test_data, "❌ Failed to retrieve from filesystem cache"
        print("   ✅ Cache retrieved from filesystem")

        # Create new cache instance with same storage (simulate restart)
        cache2 = get_cache_middleware(storage, default_ttl=300)
        cached2 = await cache2.get(tool_name, arg="test")
        assert cached2 == test_data, "❌ Cache should persist across instances"
        print("   ✅ Cache persists across cache instances")


async def main():
    """Run all cache tests."""
    print("=" * 80)
    print("Cache Middleware Test Suite")
    print("=" * 80)

    try:
        await test_cache_hit_miss()
        await test_cache_ttl_expiration()
        await test_cache_key_generation()
        await test_cache_decorator()
        await test_cache_invalidation()
        await test_cache_clear_all()
        await test_cache_with_filesystem_storage()

        print("\\n" + "=" * 80)
        print("✅ All cache tests passed!")
        print("=" * 80)

    except AssertionError as e:
        print(f"\\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
'''
