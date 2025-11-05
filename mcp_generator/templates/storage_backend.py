"""
Template for generating pluggable storage backend scaffolding.

Generates simple key-value storage interface with filesystem and in-memory backends,
plus hooks for OAuth token persistence and optional encryption.
"""


def generate_storage_backend() -> str:
    """
    Generate a pluggable storage backend module.

    Returns:
        str: Python code for storage.py module
    """
    return '''"""
Storage backend for persistent state management.

This module provides a simple key-value storage interface with multiple backends.
Designed to work standalone or integrate with py-key-value-aio for advanced use cases.

📦 Simple Out-of-the-Box Storage:
-----------------------------------
Provides filesystem and memory backends with encryption support:
- Filesystem (with Fernet encryption)
- In-memory (for testing)
- OAuth token persistence
- Simple get/set/delete API

Usage:
    from storage import get_storage

    storage = get_storage("filesystem")  # or "memory"
    await storage.set("key", "value")
    value = await storage.get("key")
    await storage.delete("key")

⚡ Upgrading to py-key-value-aio:
----------------------------------
For production deployments, you can use py-key-value-aio backends directly
with FastMCP components (ResponseCachingMiddleware, OAuth providers):

    # Install: pip install 'py-key-value-aio[redis]'
    from key_value.aio.stores.redis import RedisStore
    from fastmcp.server.middleware.caching import ResponseCachingMiddleware

    # Use directly with FastMCP middleware
    app.add_middleware(ResponseCachingMiddleware(
        cache_storage=RedisStore(host="redis.example.com")
    ))

Available py-key-value-aio backends:
- DiskStore, MemoryStore (built-in)
- RedisStore (pip install 'py-key-value-aio[redis]')
- DynamoDBStore, MongoDBStore, ElasticsearchStore, etc.

See: https://github.com/strawgate/py-key-value

Configuration:
    Set storage backend via environment variables:
    - STORAGE_BACKEND: filesystem|memory
    - STORAGE_PATH: Path for filesystem backend (default: ./.storage)
    - ENCRYPTION_KEY: Fernet encryption key (auto-generated if not set)
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

# Encryption support
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Retrieve value for key, or None if not found."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Store value for key, with optional TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from storage."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all keys (use with caution)."""
        pass


class InMemoryStorage(StorageBackend):
    """Simple in-memory storage for testing and development."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        # Note: TTL not implemented for in-memory backend
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def clear(self) -> None:
        self._store.clear()


class FilesystemStorage(StorageBackend):
    """
    Filesystem-based storage with optional encryption.

    Stores keys as files in a directory. Supports optional Fernet encryption
    for sensitive data like OAuth tokens.
    """

    def __init__(
        self,
        storage_dir: str = ".mcp_storage",
        encrypt: bool = True,
        encryption_key: Optional[str] = None
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        self.encrypt = encrypt and CRYPTO_AVAILABLE

        if self.encrypt:
            if encryption_key:
                self._fernet = Fernet(encryption_key.encode())
            else:
                # Generate or load key from file
                key_file = self.storage_dir / ".encryption_key"
                if key_file.exists():
                    key = key_file.read_bytes()
                else:
                    key = Fernet.generate_key()
                    key_file.write_bytes(key)
                    # Secure the key file (chmod 600 equivalent)
                    key_file.chmod(0o600)
                self._fernet = Fernet(key)
        elif encrypt and not CRYPTO_AVAILABLE:
            print("⚠️  Warning: cryptography not installed, encryption disabled")
            print("   Install with: pip install cryptography")

    def _get_file_path(self, key: str) -> Path:
        """Get file path for key (sanitize key name)."""
        safe_key = key.replace("/", "_").replace("\\\\", "_")
        return self.storage_dir / f"{safe_key}.dat"

    async def get(self, key: str) -> Optional[str]:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None

        data = file_path.read_bytes()

        if self.encrypt:
            data = self._fernet.decrypt(data)

        return data.decode("utf-8")

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        file_path = self._get_file_path(key)

        data = value.encode("utf-8")

        if self.encrypt:
            data = self._fernet.encrypt(data)

        file_path.write_bytes(data)
        # Note: TTL requires background cleanup task (not implemented in basic version)

    async def delete(self, key: str) -> None:
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()

    async def exists(self, key: str) -> bool:
        return self._get_file_path(key).exists()

    async def clear(self) -> None:
        for file in self.storage_dir.glob("*.dat"):
            file.unlink()


# Storage instance cache
_storage_instance: Optional[Any] = None


def get_storage(
    backend: str = "filesystem",
    **kwargs
) -> Any:
    """
    Get storage backend instance (singleton pattern).

    Args:
        backend: Backend type ("filesystem" or "memory")
        **kwargs: Additional backend-specific configuration
            - storage_dir: Directory for filesystem storage (default: .mcp_storage)
            - encrypt: Enable encryption for filesystem storage (default: True)
            - encryption_key: Custom Fernet encryption key (optional)

    Returns:
        Storage backend instance

    Example:
        # Filesystem with encryption
        storage = get_storage("filesystem", storage_dir=".data")

        # In-memory for testing
        storage = get_storage("memory")
    """
    global _storage_instance

    if _storage_instance is None:
        if backend == "memory":
            _storage_instance = InMemoryStorage()
        elif backend == "filesystem":
            _storage_instance = FilesystemStorage(**kwargs)
        else:
            raise ValueError(
                f"Unknown storage backend: {backend}. "
                f"Available: filesystem, memory"
            )

    return _storage_instance


# OAuth token persistence helpers
class TokenStore:
    """Helper class for storing OAuth tokens persistently."""

    def __init__(self, storage: Any):
        """Initialize token store with storage backend."""
        self.storage = storage

    async def save_token(self, client_id: str, token_data: dict) -> None:
        """Save OAuth token data for a client."""
        key = f"oauth:token:{client_id}"
        await self.storage.set(key, json.dumps(token_data))

    async def get_token(self, client_id: str) -> Optional[dict]:
        """Retrieve OAuth token data for a client."""
        key = f"oauth:token:{client_id}"
        data = await self.storage.get(key)
        return json.loads(data) if data else None

    async def delete_token(self, client_id: str) -> None:
        """Delete OAuth token for a client."""
        key = f"oauth:token:{client_id}"
        await self.storage.delete(key)

    async def list_clients(self) -> list[str]:
        """List all client IDs with stored tokens (filesystem only)."""
        if isinstance(self.storage, FilesystemStorage):
            tokens = []
            for file in self.storage.storage_dir.glob("oauth_token_*.dat"):
                client_id = file.stem.replace("oauth_token_", "")
                tokens.append(client_id)
            return tokens
        return []
'''
