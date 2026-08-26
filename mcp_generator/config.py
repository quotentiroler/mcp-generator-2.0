"""
MCP Generator Configuration.

Centralized configuration for name overrides, filtering, and customization.
"""

from pathlib import Path

# Bundled code templates, resolved from this module so callers in subpackages
# do not depend on their own nesting depth.
TEMPLATES_DIR = Path(__file__).parent / "templates"


# ============================================================================
# Tool Name Abbreviations
# ============================================================================
# Used to shorten long tool names to fit within MCP limits (64 chars)

TOOL_NAME_ABBREVIATIONS: dict[str, str] = {}


# ============================================================================
# Tool Name Overrides
# ============================================================================
# Custom names for specific operations (overrides auto-generated names)

TOOL_NAME_OVERRIDES: dict[str, str] = {
    # Example: 'original_operation_id': 'custom_tool_name'
    # 'list_healthcare_users_by_role': 'list_users_by_role',
    # 'create_smart_app_registration': 'register_smart_app',
}

# Maximum tool name length (MCP/OpenAI limit)
MAX_TOOL_NAME_LENGTH = 64

# Default max nesting depth for response schema parsing.
# Increase for deeply nested APIs (e.g. FHIR, Stripe).
DEFAULT_SCHEMA_DEPTH = 3


# ============================================================================
# FastMCP Target Version
# ============================================================================
# Which FastMCP major generated servers target. Matrix: fastmcp_target.py.
# Stays at 3 while 4.x is a prerelease.

DEFAULT_FASTMCP_TARGET = 3


# ============================================================================
# Project Identity
# ============================================================================
# Single source for the repo URL shown in CLI output and generated headers.

PROJECT_REPO_URL = "https://github.com/quotentiroler/mcp-generator-3.x"
PROJECT_ISSUES_URL = f"{PROJECT_REPO_URL}/issues"


# ============================================================================
# Client-Requiring MCP Methods
# ============================================================================
# Handlers that read the API client from state. The generated auth middleware
# skips every other method. Verified on both protocol eras (fastmcp 4.0.0b3).

CLIENT_REQUIRED_MCP_METHODS: tuple[str, ...] = (
    "tools/call",
    "resources/read",
)


# ============================================================================
# Security Defaults
# ============================================================================
# Scopes applied when the OpenAPI spec declares no global security requirement.
# Empty by design: a spec that asks for no scopes should not have one invented
# for it. Override only when a backend enforces a scope it fails to advertise.

DEFAULT_FALLBACK_SCOPES: list[str] = []
