"""Resolves $refs and parses response schemas into typed fields."""

from __future__ import annotations

from typing import Any

from ..models import (
    ResponseField,
    ResponseSchema,
)

# ---------------------------------------------------------------------------
# Phase 2: Response schema extraction for generated display tools
# ---------------------------------------------------------------------------

_OPENAPI_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


_ref_cache: dict[tuple[int, str], dict[str, Any]] = {}


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a $ref pointer (e.g. '#/components/schemas/Pet') within the spec.

    Results are cached per (spec identity, ref) for performance on large specs.
    """
    cache_key = (id(spec), ref)
    if cache_key in _ref_cache:
        return _ref_cache[cache_key]

    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            _ref_cache[cache_key] = {}
            return {}
    result = node if isinstance(node, dict) else {}
    _ref_cache[cache_key] = result
    return result


def _ref_name(ref: str) -> str:
    """Extract the schema name from a $ref string (e.g. 'Pet' from '#/components/schemas/Pet')."""
    return ref.rsplit("/", 1)[-1] if "/" in ref else ref


def _parse_schema_fields(
    schema: dict[str, Any],
    spec: dict[str, Any],
    depth: int = 0,
    max_depth: int = 3,
    visited: set[str] | None = None,
) -> list[ResponseField]:
    """Recursively parse an object schema's properties into ResponseField list.

    Handles $ref resolution, nested objects, arrays, and enums.
    Stops at max_depth to prevent infinite recursion from circular $refs.
    """
    if depth >= max_depth:
        return []
    if visited is None:
        visited = set()

    # Resolve $ref at the schema level
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in visited:
            return []  # Break circular reference
        visited = visited | {ref}
        schema = _resolve_ref(spec, ref)

    # Handle allOf / oneOf / anyOf — merge properties from all variants
    for combiner in ("allOf", "oneOf", "anyOf"):
        if combiner in schema and schema[combiner]:
            merged_props: dict[str, Any] = {}
            for sub in schema[combiner]:
                resolved = _resolve_ref(spec, sub["$ref"]) if "$ref" in sub else sub
                merged_props.update(resolved.get("properties", {}))
            schema = {"type": "object", "properties": merged_props}
            break

    properties = schema.get("properties", {})
    fields: list[ResponseField] = []

    for prop_name, prop_schema in properties.items():
        # Resolve property-level $ref
        resolved_prop = prop_schema
        if "$ref" in prop_schema:
            ref = prop_schema["$ref"]
            if ref in visited:
                continue
            resolved_prop = _resolve_ref(spec, ref)

        prop_type = resolved_prop.get("type", "string")
        fmt = resolved_prop.get("format", "")

        # OpenAPI 3.1: nullable types use type: ["string", "null"]
        if isinstance(prop_type, list):
            non_null = [t for t in prop_type if t != "null"]
            prop_type = non_null[0] if non_null else "string"

        # Enum
        enum_values = resolved_prop.get("enum", [])
        is_enum = bool(enum_values)

        # Nested object
        is_nested_object = prop_type == "object" and "properties" in resolved_prop
        has_combiner = any(c in resolved_prop for c in ("allOf", "oneOf", "anyOf"))
        nested_fields: list[ResponseField] = []
        if is_nested_object or "$ref" in prop_schema or has_combiner:
            nested_fields = _parse_schema_fields(resolved_prop, spec, depth + 1, max_depth, visited)
            is_nested_object = bool(nested_fields)

        # Array with items
        is_array = prop_type == "array"
        if is_array and "items" in resolved_prop:
            items_schema = resolved_prop["items"]
            if "$ref" in items_schema or items_schema.get("type") == "object":
                nested_fields = _parse_schema_fields(
                    items_schema, spec, depth + 1, max_depth, visited
                )

        fields.append(
            ResponseField(
                name=prop_name,
                python_type=_OPENAPI_TYPE_MAP.get(prop_type, "str"),
                description=resolved_prop.get("description", ""),
                is_enum=is_enum,
                enum_values=[str(v) for v in enum_values],
                is_nested_object=is_nested_object,
                is_array=is_array,
                nested_fields=nested_fields,
                format=fmt,
            )
        )

    return fields


def _extract_response_schema(
    responses: dict[str, Any], spec: dict[str, Any], *, max_depth: int = 3
) -> ResponseSchema | None:
    """Extract and parse the success response schema from an endpoint's responses dict."""
    # Find the success response (200, 201, or default)
    success_resp = responses.get("200", responses.get("201", responses.get("default")))
    if not success_resp:
        return None

    # Resolve response-level $ref (e.g. {"$ref": "#/components/responses/PetResponse"})
    if "$ref" in success_resp:
        success_resp = _resolve_ref(spec, success_resp["$ref"])

    content = success_resp.get("content", {})
    json_content = (
        content.get("application/json")
        or content.get("application/fhir+json")
        or content.get("*/*")
        or {}
    )
    schema = json_content.get("schema", {})

    if not schema:
        return None

    # Resolve top-level $ref
    schema_name = ""
    if "$ref" in schema:
        schema_name = _ref_name(schema["$ref"])
        schema = _resolve_ref(spec, schema["$ref"])

    top_type = schema.get("type", "")

    # Skip: additionalProperties-only (dynamic maps), scalars
    if top_type in ("string", "number", "integer", "boolean"):
        return None
    if top_type == "object" and "additionalProperties" in schema and "properties" not in schema:
        return None

    # Array of objects
    if top_type == "array":
        items = schema.get("items", {})
        if "$ref" in items:
            schema_name = schema_name or _ref_name(items["$ref"])
        fields = _parse_schema_fields(items, spec, max_depth=max_depth)
        if not fields:
            return None
        return ResponseSchema(fields=fields, is_array=True, schema_name=schema_name)

    # Single object
    fields = _parse_schema_fields(schema, spec, max_depth=max_depth)
    if not fields:
        return None
    return ResponseSchema(fields=fields, is_object=True, schema_name=schema_name)
