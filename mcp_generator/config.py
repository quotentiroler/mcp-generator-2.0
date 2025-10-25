"""
MCP Generator Configuration.

Centralized configuration for name overrides, filtering, and customization.
"""



# ============================================================================
# Tool Name Abbreviations
# ============================================================================
# Used to shorten long tool names to fit within MCP limits (64 chars)

TOOL_NAME_ABBREVIATIONS = { }


# ============================================================================
# Tool Name Overrides
# ============================================================================
# Custom names for specific operations (overrides auto-generated names)

TOOL_NAME_OVERRIDES = {
    # Example: 'original_operation_id': 'custom_tool_name'
    # 'list_healthcare_users_by_role': 'list_users_by_role',
    # 'create_smart_app_registration': 'register_smart_app',
}

# Maximum tool name length (MCP/OpenAI limit)
MAX_TOOL_NAME_LENGTH = 64
