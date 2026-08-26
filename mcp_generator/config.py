"""
MCP Generator Configuration.

Centralized configuration for name overrides, filtering, and customization.
"""


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
# Which FastMCP major the generated servers target. See fastmcp_target.py for
# the per-major matrix. Stays at 3 while 4.x is a prerelease; the 3.x line is
# upstream's supported maintenance branch for MCP SDK v1 users.

DEFAULT_FASTMCP_TARGET = 3


# ============================================================================
# Security Defaults
# ============================================================================
# Scopes applied when the OpenAPI spec declares no global security requirement.
# Empty by design: a spec that asks for no scopes should not have one invented
# for it. Override only when a backend enforces a scope it fails to advertise.

DEFAULT_FALLBACK_SCOPES: list[str] = []
