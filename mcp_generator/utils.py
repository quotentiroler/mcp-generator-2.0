"""
Utility functions for MCP generator.

Provides helper functions for name sanitization, schema extraction,
and parameter description formatting.
"""

import json
import re
from typing import Any, get_origin, get_type_hints

from .config import MAX_TOOL_NAME_LENGTH, TOOL_NAME_ABBREVIATIONS, TOOL_NAME_OVERRIDES


def normalize_version(version: str) -> str:
    """
    Normalize version string to be PEP 440 compliant.

    Examples:
        "0.0.1-alpha.202510200205.3df5db6a" -> "0.0.1a0+202510200205.3df5db6a"
        "1.2.3-beta.456" -> "1.2.3b0+456"
        "2.0.0" -> "2.0.0"
    """
    # Pattern: version-prerelease.local -> version+prerelease.local
    # Convert: X.Y.Z-alpha.A.B -> X.Y.Za0+A.B
    # Convert: X.Y.Z-beta.A.B -> X.Y.Zb0+A.B

    # Match version-prerelease.rest pattern
    match = re.match(r'^(\d+\.\d+\.\d+)-([a-z]+)\.(.+)$', version)
    if match:
        base_version, prerelease, local = match.groups()

        # Map prerelease identifiers to PEP 440 format
        prerelease_map = {
            'alpha': 'a',
            'beta': 'b',
            'rc': 'rc',
            'dev': 'dev',
        }

        prerelease_short = prerelease_map.get(prerelease, prerelease[:1])

        # PEP 440 format: base_version + prerelease_short + 0 + '+' + local
        return f"{base_version}{prerelease_short}0+{local}"

    # If no match, return as-is (already valid or will fail validation)
    return version


def sanitize_name(name: str) -> str:
    """
    Convert API method name to MCP tool name.

    1. Check for custom override in TOOL_NAME_OVERRIDES
    2. Map HTTP verbs to semantic action verbs:
       - get_users → list_users (for collection endpoints)
       - get_user_by_id → get_user_by_id (for singular endpoints)
       - post_users → create_users
       - put_user_by_id → update_user_by_id
       - delete_user_by_id → delete_user_by_id
    3. Apply abbreviations from TOOL_NAME_ABBREVIATIONS if name exceeds MAX_TOOL_NAME_LENGTH
    """
    original_name = name

    # 1. Check for custom override first
    if original_name in TOOL_NAME_OVERRIDES:
        return TOOL_NAME_OVERRIDES[original_name]

    # 2. Map HTTP verbs to semantic action verbs
    verb_mapping = {
        'get': 'list',  # GET collection
        'post': 'create',
        'put': 'replace',  # PUT = full replacement
        'patch': 'update',  # PATCH = partial update
        'delete': 'delete',
    }

    # Extract HTTP verb prefix if present
    match = re.match(r'^(get|post|put|delete|patch)_(.+)$', name)
    if match:
        verb, rest = match.groups()

        # Keep 'by_' parts (they indicate specific resource)
        # For GET without 'by_', it's a list operation
        if verb == 'get' and '_by_' not in name:
            # GET collection → list
            semantic_verb = 'list'
        elif verb == 'get' and '_by_' in name:
            # GET specific resource → get
            semantic_verb = 'get'
        else:
            # POST/PUT/DELETE → use mapping
            semantic_verb = verb_mapping.get(verb, verb)

        name = f"{semantic_verb}_{rest}"

    # Convert camelCase to snake_case
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    name = name.lower()

    # 3. Apply abbreviations if name is too long
    if len(name) > MAX_TOOL_NAME_LENGTH:
        for long_form, short_form in TOOL_NAME_ABBREVIATIONS.items():
            name = name.replace(long_form, short_form)
            # Stop early if we're under the limit
            if len(name) <= MAX_TOOL_NAME_LENGTH:
                break

    return name


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def get_pydantic_model_schema(model_class) -> dict[str, Any] | None:
    """Extract schema information from a Pydantic model."""
    try:
        # Check if it's a Pydantic model
        if not hasattr(model_class, 'model_fields'):
            return None

        schema = {
            "fields": {},
            "required": [],
            "example": {}
        }

        # Extract field information
        for field_name, field_info in model_class.model_fields.items():
            field_schema = {
                "type": str(field_info.annotation),
                "description": field_info.description or "",
                "required": field_info.is_required(),
                "alias": field_info.alias or field_name
            }

            schema["fields"][field_name] = field_schema

            if field_info.is_required():
                schema["required"].append(field_name)

            # Build example value
            if field_info.is_required():
                if 'str' in str(field_info.annotation).lower():
                    if 'email' in field_name.lower():
                        schema["example"][field_info.alias or field_name] = "user@example.com"
                    elif 'name' in field_name.lower():
                        schema["example"][field_info.alias or field_name] = "Example Name"
                    elif 'username' in field_name.lower():
                        schema["example"][field_info.alias or field_name] = "username"
                    else:
                        schema["example"][field_info.alias or field_name] = f"<{field_name}>"
                elif 'bool' in str(field_info.annotation).lower():
                    schema["example"][field_info.alias or field_name] = False
                elif 'int' in str(field_info.annotation).lower():
                    schema["example"][field_info.alias or field_name] = 0

        return schema
    except Exception:
        return None


def format_parameter_description(param_name: str, param_type: Any, method) -> tuple[str, str | None]:
    """
    Generate enhanced parameter description with schema details.
    Returns (description, example_json)
    """
    # Try to extract the actual type from annotations
    try:
        hints = get_type_hints(method)
        if param_name in hints:
            hint = hints[param_name]

            # Check if it's a Pydantic model (has model_fields)
            origin = get_origin(hint)
            if origin is None:
                # Direct type, might be a Pydantic model
                if hasattr(hint, 'model_fields'):
                    schema = get_pydantic_model_schema(hint)
                    if schema:
                        # Build detailed description
                        desc_parts = ["JSON object with the following fields:"]

                        for _field_name, field_info in schema["fields"].items():
                            req = "REQUIRED" if field_info["required"] else "optional"
                            alias = field_info["alias"]
                            field_desc = field_info["description"]
                            desc_parts.append(f"  - {alias} ({req}): {field_desc}" if field_desc else f"  - {alias} ({req})")

                        description = "\n".join(desc_parts)
                        example_json = json.dumps(schema["example"], indent=2)

                        return description, example_json
    except Exception:
        pass

    # Fallback to simple description
    return f"Parameter: {param_name}", None
