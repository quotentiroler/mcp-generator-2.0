"""Console setup and human-readable generation summaries."""

import os
import sys
from typing import Any


def setup_utf8_console() -> None:
    """Configure UTF-8 encoding for console output (fixes emoji display on Windows)."""
    if sys.platform == "win32":
        # Set console to UTF-8 mode on Windows
        os.system("chcp 65001 > nul 2>&1")
        # Reconfigure stdout encoding if available (Python 3.7+)
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass  # Not available or failed, continue anyway


def print_metadata_summary(api_metadata: Any, security_config: Any) -> None:
    """Print API metadata and security configuration summary."""
    print("\n📋 API Metadata:")
    print(f"   Title: {api_metadata.title}")
    print(f"   Version: {api_metadata.version}")
    if api_metadata.description:
        print(f"   Description: {api_metadata.description[:80]}...")
    if api_metadata.contact and api_metadata.contact.get("email"):
        print(f"   Contact: {api_metadata.contact['email']}")
    if api_metadata.license and api_metadata.license.get("name"):
        print(f"   License: {api_metadata.license['name']}")
    if api_metadata.servers:
        print(f"   Servers: {len(api_metadata.servers)} configured")
    if api_metadata.tags:
        print(f"   Tags: {len(api_metadata.tags)} categories")

    backend_url = api_metadata.backend_url
    print(f"   Backend URL: {backend_url}")
    if api_metadata.has_relative_server_url:
        print(f"\n   ⚠️  WARNING: Server URL '{backend_url}' is relative (no host).")
        print("   The generated code will not work without setting API_BASE_URL at runtime.")
        print("   Set it via environment variable or in your MCP client config, e.g.:")
        print("   API_BASE_URL=https://your-api-host.com/api/v3")

    print("\n🔐 Security Configuration:")
    if security_config.schemes:
        print(f"   Authentication: {', '.join(security_config.schemes.keys())}")
    if security_config.default_scopes:
        print(f"   Default scopes: {', '.join(security_config.default_scopes)}")
    if security_config.oauth_config:
        oauth = security_config.oauth_config
        print(f"   OAuth2 flows: {', '.join(oauth.flows.keys())}")
        print(f"   Available scopes: {len(oauth.all_scopes)}")
