"""Discovers display, form and delete endpoints for generated UI tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import (
    DeleteEndpoint,
    DisplayEndpoint,
    FormEndpoint,
    ResponseField,
)
from ..utils import camel_to_snake
from .schema import (
    _extract_response_schema,
    _parse_schema_fields,
    _ref_name,
    _resolve_ref,
)
from .spec import _find_openapi_spec, _load_openapi_spec, enrich_spec_tags


def get_display_endpoints(
    base_dir: Path | None = None,
    *,
    max_depth: int = 3,
    spec: dict[str, Any] | None = None,
) -> dict[str, list[DisplayEndpoint]]:
    """Extract GET endpoints with parsed response schemas for display tool generation.

    Args:
        base_dir: Directory containing the OpenAPI spec (fallback when *spec* is None).
        max_depth: Maximum nesting depth for response schema parsing.
        spec: Pre-loaded OpenAPI spec dict.  When provided the file-system
              lookup is skipped, which ensures overlay-enhanced specs are used.

    Returns:
        Dictionary mapping tag names to lists of DisplayEndpoint with resolved schemas.
    """
    if spec is None:
        if base_dir is None:
            base_dir = Path.cwd()
        openapi_path = _find_openapi_spec(base_dir)
        if not openapi_path or not openapi_path.exists():
            return {}
        spec = _load_openapi_spec(openapi_path)
    if not spec or "paths" not in spec:
        return {}

    enrich_spec_tags(spec)
    endpoints_by_tag: dict[str, list[DisplayEndpoint]] = {}

    for path, path_item in spec.get("paths", {}).items():
        if "get" not in path_item:
            continue

        get_op = path_item["get"]
        operation_id = get_op.get("operationId")
        if not operation_id:
            continue

        responses = get_op.get("responses", {})
        response_schema = _extract_response_schema(responses, spec, max_depth=max_depth)

        # Skip endpoints without parseable response schemas
        if response_schema is None:
            continue

        tags = get_op.get("tags", ["default"])
        primary_tag = tags[0] if tags else "default"

        path_params = []
        query_params = []

        # Merge path-level + operation-level params; resolve $ref; deduplicate
        all_display_params = list(path_item.get("parameters", []))
        for op_param in get_op.get("parameters", []):
            all_display_params.append(op_param)
        seen_display: set[str] = set()
        deduped_display: list[dict[str, Any]] = []
        for param in reversed(all_display_params):
            if "$ref" in param:
                param = _resolve_ref(spec, param["$ref"])
            name = param.get("name")
            if name and name not in seen_display:
                seen_display.add(name)
                deduped_display.append(param)
        deduped_display.reverse()

        for param in deduped_display:
            p_in = param.get("in")
            if p_in == "path":
                path_params.append(
                    {
                        "name": param.get("name"),
                        "schema": param.get("schema", {}),
                        "required": True,
                    }
                )
            elif p_in == "query":
                query_params.append(
                    {
                        "name": param.get("name"),
                        "required": param.get("required", False),
                        "schema": param.get("schema", {}),
                        "description": param.get("description", ""),
                    }
                )

        endpoint = DisplayEndpoint(
            operation_id=operation_id,
            path=path,
            http_method="get",
            summary=get_op.get("summary", ""),
            tag=primary_tag,
            path_params=path_params,
            query_params=query_params,
            response_schema=response_schema,
        )

        if primary_tag not in endpoints_by_tag:
            endpoints_by_tag[primary_tag] = []
        endpoints_by_tag[primary_tag].append(endpoint)

    return endpoints_by_tag


# ---------------------------------------------------------------------------
# Phase 3: Request body schema extraction for form generation
# ---------------------------------------------------------------------------


def _extract_request_body_schema(
    operation: dict[str, Any], spec: dict[str, Any]
) -> tuple[str, list[ResponseField], list[str]] | None:
    """Extract the request body schema from a POST/PUT operation.

    Returns:
        (schema_name, fields, required_field_names) or None if no parseable body.
    """
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})

    # Prefer JSON content type
    json_content = content.get("application/json", content.get("*/*", {}))
    schema = json_content.get("schema", {})
    if not schema:
        return None

    schema_name = ""
    if "$ref" in schema:
        schema_name = _ref_name(schema["$ref"])
        schema = _resolve_ref(spec, schema["$ref"])

    if schema.get("type") != "object" and "properties" not in schema:
        return None

    fields = _parse_schema_fields(schema, spec)
    if not fields:
        return None

    required_names = schema.get("required", [])
    return schema_name, fields, required_names


def get_form_endpoints(
    base_dir: Path | None = None,
    *,
    max_depth: int = 3,
    spec: dict[str, Any] | None = None,
) -> dict[str, list[FormEndpoint]]:
    """Extract POST/PUT endpoints with request body schemas for form generation.

    Args:
        base_dir: Directory containing the OpenAPI spec (fallback when *spec* is None).
        max_depth: Maximum nesting depth for request body schema parsing.
        spec: Pre-loaded OpenAPI spec dict.  When provided the file-system
              lookup is skipped, which ensures overlay-enhanced specs are used.

    Returns:
        Dictionary mapping tag names to lists of FormEndpoint.
    """
    if spec is None:
        if base_dir is None:
            base_dir = Path.cwd()
        openapi_path = _find_openapi_spec(base_dir)
        if not openapi_path or not openapi_path.exists():
            return {}
        spec = _load_openapi_spec(openapi_path)
    if not spec or "paths" not in spec:
        return {}

    enrich_spec_tags(spec)
    forms_by_tag: dict[str, list[FormEndpoint]] = {}

    for path, path_item in spec.get("paths", {}).items():
        for method in ("post", "put"):
            if method not in path_item:
                continue

            op = path_item[method]
            operation_id = op.get("operationId")
            if not operation_id:
                continue

            result = _extract_request_body_schema(op, spec)
            if result is None:
                continue

            schema_name, fields, required_names = result

            tags = op.get("tags", ["default"])
            primary_tag = tags[0] if tags else "default"

            # Build MCP tool name: {Tag}_{snake_case_op} matching namespace mount
            snake_op = camel_to_snake(operation_id)
            tool_name = f"{primary_tag.title()}_{snake_op}"

            endpoint = FormEndpoint(
                operation_id=operation_id,
                path=path,
                http_method=method,
                summary=op.get("summary", ""),
                tag=primary_tag,
                schema_name=schema_name,
                fields=fields,
                required_fields=required_names,
                tool_name=tool_name,
            )

            if primary_tag not in forms_by_tag:
                forms_by_tag[primary_tag] = []
            forms_by_tag[primary_tag].append(endpoint)

    return forms_by_tag


def get_delete_endpoints(
    base_dir: Path | None = None,
    *,
    spec: dict[str, Any] | None = None,
) -> dict[str, list[DeleteEndpoint]]:
    """Extract DELETE endpoints for generating delete confirmation dialogs.

    Args:
        base_dir: Directory containing the OpenAPI spec (fallback when *spec* is None).
        spec: Pre-loaded OpenAPI spec dict.  When provided the file-system
              lookup is skipped, which ensures overlay-enhanced specs are used.

    Returns:
        Dictionary mapping tag names to lists of DeleteEndpoint.
    """
    if spec is None:
        if base_dir is None:
            base_dir = Path.cwd()
        openapi_path = _find_openapi_spec(base_dir)
        if not openapi_path or not openapi_path.exists():
            return {}
        spec = _load_openapi_spec(openapi_path)
    if not spec or "paths" not in spec:
        return {}

    enrich_spec_tags(spec)
    deletes_by_tag: dict[str, list[DeleteEndpoint]] = {}

    for path, path_item in spec.get("paths", {}).items():
        if "delete" not in path_item:
            continue

        op = path_item["delete"]
        operation_id = op.get("operationId")
        if not operation_id:
            continue

        tags = op.get("tags", ["default"])
        primary_tag = tags[0] if tags else "default"

        # Collect path parameters (DELETE typically needs an ID)
        path_params: list[dict[str, Any]] = []
        all_params = list(path_item.get("parameters", []))
        for op_param in op.get("parameters", []):
            all_params.append(op_param)
        seen: set[str] = set()
        for param in reversed(all_params):
            if "$ref" in param:
                param = _resolve_ref(spec, param["$ref"])
            name = param.get("name")
            p_in = param.get("in")
            if name and name not in seen and p_in == "path":
                seen.add(name)
                path_params.append(
                    {
                        "name": name,
                        "schema": param.get("schema", {}),
                        "required": True,
                    }
                )

        # Build MCP tool name: {Tag}_{snake_case_op} matching namespace mount
        snake_op = camel_to_snake(operation_id)
        tool_name = f"{primary_tag.title()}_{snake_op}"

        endpoint = DeleteEndpoint(
            operation_id=operation_id,
            path=path,
            summary=op.get("summary", ""),
            tag=primary_tag,
            path_params=path_params,
            tool_name=tool_name,
        )

        if primary_tag not in deletes_by_tag:
            deletes_by_tag[primary_tag] = []
        deletes_by_tag[primary_tag].append(endpoint)

    return deletes_by_tag


# ---------------------------------------------------------------------------
# Phase 4: Body schema extraction for form data coercion
# ---------------------------------------------------------------------------
