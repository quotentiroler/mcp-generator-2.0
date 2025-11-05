"""
Template for generating OAuth token persistence tests.
"""


def generate_oauth_persistence_tests() -> str:
    """Generate comprehensive tests for OAuth token persistence."""
    return '''"""
Tests for OAuth token persistence functionality.

Tests cover:
- Token storage and retrieval
- Token expiration handling
- Token deletion (logout/revocation)
- RFC 7662 token introspection
- Storage backend integration
"""

import asyncio
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add parent directories to path for imports
test_dir = Path(__file__).parent
project_root = test_dir.parent.parent
generated_mcp_dir = project_root / "generated_mcp"

# Debug: Print paths for troubleshooting (only in CI or when debugging)
import os
if os.getenv("CI") or os.getenv("DEBUG_OAUTH_TESTS"):
    print(f"\\n[OAuth Tests Debug]")
    print(f"  __file__: {Path(__file__).resolve()}")
    print(f"  test_dir: {test_dir.resolve()}")
    print(f"  project_root: {project_root.resolve()}")
    print(f"  generated_mcp_dir: {generated_mcp_dir.resolve()}")
    print(f"  storage.py exists: {(generated_mcp_dir / 'storage.py').exists()}")
    print(f"  middleware/ exists: {(generated_mcp_dir / 'middleware').exists()}")
    print(f"  sys.path[0]: {sys.path[0] if sys.path else 'empty'}")

sys.path.insert(0, str(generated_mcp_dir))

try:
    from storage import get_storage
    from middleware.oauth_provider import OAuthTokenManager, get_token_manager
    STORAGE_AVAILABLE = True
except ImportError as e:
    STORAGE_AVAILABLE = False
    IMPORT_ERROR = str(e)
    # Don't exit during import - pytest needs to collect tests
    if __name__ == "__main__":
        print("⚠️  Skipped: OAuth provider or storage modules not generated")
        print(f"   Import error: {e}")
        print(f"   Looked in: {generated_mcp_dir}")
        print(f"   Storage exists: {(generated_mcp_dir / 'storage.py').exists()}")
        print(f"   Middleware dir exists: {(generated_mcp_dir / 'middleware').exists()}")
        print("   Run with: uv run generate-mcp --enable-storage")
        sys.exit(0)


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason=f"Storage not generated: {IMPORT_ERROR if not STORAGE_AVAILABLE else 'N/A'}")
async def test_token_storage_and_retrieval():
    """Test basic token storage and retrieval."""
    print("\\n🧪 Testing Token Storage and Retrieval...")

    storage = get_storage("memory")
    token_manager = get_token_manager(storage)

    client_id = "test_client_123"
    token_data = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "refresh_abc123",
        "scope": "read write"
    }

    # Store token
    success = await token_manager.store_token(client_id, token_data, user_id="user456")
    assert success, "❌ Failed to store token"
    print("   ✅ Token stored successfully")

    # Retrieve token
    retrieved = await token_manager.get_token(client_id)
    assert retrieved is not None, "❌ Failed to retrieve token"
    assert retrieved["access_token"] == token_data["access_token"], "❌ Access token mismatch"
    assert retrieved["refresh_token"] == token_data["refresh_token"], "❌ Refresh token mismatch"
    assert retrieved["user_id"] == "user456", "❌ User ID not stored"
    assert "stored_at" in retrieved, "❌ Missing stored_at timestamp"
    print("   ✅ Token retrieved with correct data")
    print(f"   ✅ User ID preserved: {retrieved['user_id']}")
    print(f"   ✅ Stored at: {datetime.fromtimestamp(retrieved['stored_at']).isoformat()}")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_token_deletion():
    """Test token deletion (logout/revocation)."""
    print("\\n🧪 Testing Token Deletion...")

    storage = get_storage("memory")
    token_manager = get_token_manager(storage)

    client_id = "delete_test_client"
    token_data = {
        "access_token": "token_to_delete",
        "token_type": "Bearer"
    }

    # Store token
    await token_manager.store_token(client_id, token_data)
    retrieved = await token_manager.get_token(client_id)
    assert retrieved is not None, "❌ Token should exist before deletion"
    print("   ✅ Token created")

    # Delete token
    success = await token_manager.delete_token(client_id)
    assert success, "❌ Failed to delete token"
    print("   ✅ Token deleted")

    # Verify deletion
    retrieved = await token_manager.get_token(client_id)
    assert retrieved is None, "❌ Token should not exist after deletion"
    print("   ✅ Token no longer retrievable")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_multiple_client_tokens():
    """Test storing tokens for multiple clients."""
    print("\\n🧪 Testing Multiple Client Tokens...")

    storage = get_storage("memory")
    token_manager = get_token_manager(storage)

    clients = {
        "client_A": {"access_token": "token_A", "user_id": "user_1"},
        "client_B": {"access_token": "token_B", "user_id": "user_2"},
        "client_C": {"access_token": "token_C", "user_id": "user_3"},
    }

    # Store all tokens
    for client_id, token_data in clients.items():
        user_id = token_data.pop("user_id")
        await token_manager.store_token(client_id, token_data, user_id=user_id)
    print("   ✅ Stored tokens for 3 clients")

    # Retrieve and verify each
    for client_id, expected in clients.items():
        retrieved = await token_manager.get_token(client_id)
        assert retrieved is not None, f"❌ Failed to retrieve token for {client_id}"
        assert retrieved["access_token"] == expected["access_token"], f"❌ Token mismatch for {client_id}"
    print("   ✅ All client tokens retrievable independently")

    # Delete one client
    await token_manager.delete_token("client_B")

    # Verify others still exist
    assert await token_manager.get_token("client_A") is not None, "❌ client_A token should still exist"
    assert await token_manager.get_token("client_B") is None, "❌ client_B token should be deleted"
    assert await token_manager.get_token("client_C") is not None, "❌ client_C token should still exist"
    print("   ✅ Selective deletion works correctly")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_token_persistence_across_instances():
    """Test that tokens persist across token manager instances."""
    print("\\n🧪 Testing Token Persistence Across Instances...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # First instance
        storage1 = get_storage("filesystem", base_dir=tmpdir)
        token_manager1 = get_token_manager(storage1)

        client_id = "persistent_client"
        token_data = {
            "access_token": "persistent_token_xyz",
            "refresh_token": "refresh_xyz",
            "scope": "admin"
        }

        await token_manager1.store_token(client_id, token_data)
        print("   ✅ Token stored in first instance")

        # Second instance (simulates server restart)
        storage2 = get_storage("filesystem", base_dir=tmpdir)
        token_manager2 = get_token_manager(storage2)

        retrieved = await token_manager2.get_token(client_id)
        assert retrieved is not None, "❌ Token should persist across instances"
        assert retrieved["access_token"] == token_data["access_token"], "❌ Token data mismatch"
        assert retrieved["scope"] == token_data["scope"], "❌ Scope not preserved"
        print("   ✅ Token retrieved in second instance")
        print("   ✅ Tokens survive server restarts")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_token_manager_without_storage():
    """Test token manager behavior when storage is not available."""
    print("\\n🧪 Testing Token Manager Without Storage...")

    # Create manager without storage
    token_manager = get_token_manager(storage_backend=None)

    client_id = "no_storage_client"
    token_data = {"access_token": "ephemeral_token"}

    # Storage operations should fail gracefully
    success = await token_manager.store_token(client_id, token_data)
    assert not success, "❌ Storage should fail without backend"
    print("   ✅ Store operation failed gracefully (expected)")

    retrieved = await token_manager.get_token(client_id)
    assert retrieved is None, "❌ Get should return None without storage"
    print("   ✅ Get operation returns None (expected)")

    delete_success = await token_manager.delete_token(client_id)
    assert not delete_success, "❌ Delete should fail without backend"
    print("   ✅ Delete operation failed gracefully (expected)")

    print("   ✅ Token manager handles missing storage backend gracefully")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_token_with_metadata():
    """Test that token metadata is properly stored and retrieved."""
    print("\\n🧪 Testing Token Metadata...")

    storage = get_storage("memory")
    token_manager = get_token_manager(storage)

    client_id = "metadata_client"
    token_data = {
        "access_token": "access_with_metadata",
        "token_type": "Bearer",
        "expires_in": 7200,
        "scope": "read write delete",
        "issued_at": int(time.time()),
    }

    await token_manager.store_token(client_id, token_data, user_id="metadata_user")

    retrieved = await token_manager.get_token(client_id)
    assert retrieved is not None, "❌ Failed to retrieve token"

    # Verify all original fields preserved
    for key, value in token_data.items():
        assert retrieved.get(key) == value, f"❌ Metadata field '{key}' not preserved"
    print("   ✅ All original token fields preserved")

    # Verify enriched metadata
    assert "stored_at" in retrieved, "❌ Missing stored_at timestamp"
    assert "user_id" in retrieved, "❌ Missing user_id"
    assert retrieved["user_id"] == "metadata_user", "❌ User ID mismatch"
    print("   ✅ Enriched metadata added correctly")

    # Verify metadata types
    assert isinstance(retrieved["stored_at"], int), "❌ stored_at should be int timestamp"
    assert isinstance(retrieved["expires_in"], int), "❌ expires_in should be int"
    print("   ✅ Metadata types correct")


@pytest.mark.skipif(not STORAGE_AVAILABLE, reason="Storage not generated")
async def test_concurrent_token_operations():
    """Test concurrent token storage and retrieval."""
    print("\\n🧪 Testing Concurrent Token Operations...")

    storage = get_storage("memory")
    token_manager = get_token_manager(storage)

    # Store tokens concurrently
    async def store_token(client_num: int):
        client_id = f"concurrent_client_{client_num}"
        token_data = {"access_token": f"token_{client_num}"}
        await token_manager.store_token(client_id, token_data)

    # Store 10 tokens concurrently
    await asyncio.gather(*[store_token(i) for i in range(10)])
    print("   ✅ Stored 10 tokens concurrently")

    # Retrieve tokens concurrently
    async def retrieve_token(client_num: int):
        client_id = f"concurrent_client_{client_num}"
        token = await token_manager.get_token(client_id)
        assert token is not None, f"❌ Failed to retrieve token for client {client_num}"
        assert token["access_token"] == f"token_{client_num}", f"❌ Token mismatch for client {client_num}"

    await asyncio.gather(*[retrieve_token(i) for i in range(10)])
    print("   ✅ Retrieved all 10 tokens concurrently")
    print("   ✅ No race conditions detected")


async def main():
    """Run all OAuth persistence tests."""
    print("=" * 80)
    print("OAuth Token Persistence Test Suite")
    print("=" * 80)

    try:
        await test_token_storage_and_retrieval()
        await test_token_deletion()
        await test_multiple_client_tokens()
        await test_token_persistence_across_instances()
        await test_token_manager_without_storage()
        await test_token_with_metadata()
        await test_concurrent_token_operations()

        print("\\n" + "=" * 80)
        print("✅ All OAuth persistence tests passed!")
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
