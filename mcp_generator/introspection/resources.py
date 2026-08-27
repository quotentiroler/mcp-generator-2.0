"""Discovers GET endpoints that become MCP resource templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .schema import _resolve_ref
from .spec import _find_openapi_spec, _load_openapi_spec, enrich_spec_tags


def get_resource_endpoints(base_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """
    Extract GET endpoints from OpenAPI spec that are suitable for resource templates.

    Resources are best suited for:
    - GET endpoints with path parameters (e.g., /pet/{petId})
    - Read-only operations that return structured data
    - Endpoints that naturally map to URI templates

    Args:
        base_dir: Base directory containing openapi files. Defaults to current working directory.

    Returns:
        Dictionary mapping API tag names to lists of resource endpoint specs
    """
    if base_dir is None:
        base_dir = Path.cwd()

    openapi_path = _find_openapi_spec(base_dir)

    if not openapi_path or not openapi_path.exists():
        return {}

    spec = _load_openapi_spec(openapi_path)

    if not spec or "paths" not in spec:
        return {}

    # Enrich tags before grouping resources
    enrich_spec_tags(spec)

    resources_by_tag: dict[str, list[dict[str, Any]]] = {}

    for path, path_item in spec.get("paths", {}).items():
        # Only process GET methods
        if "get" not in path_item:
            continue

        get_op = path_item["get"]
        operation_id = get_op.get("operationId")

        if not operation_id:
            continue

        # Extract tags (for grouping by API module)
        tags = get_op.get("tags", ["default"])
        primary_tag = tags[0] if tags else "default"

        # Extract path parameters (e.g., {petId})
        path_params = []
        query_params = []

        # Merge path-level + operation-level parameters (operation takes precedence)
        all_params = list(path_item.get("parameters", []))
        for op_param in get_op.get("parameters", []):
            all_params.append(op_param)
        # Deduplicate: keep operation-level params, skip path-level if same name
        seen_names: set[str] = set()
        deduped_params = []
        for param in reversed(all_params):
            # Resolve $ref parameters
            if "$ref" in param:
                param = _resolve_ref(spec, param["$ref"])
            name = param.get("name")
            if name and name not in seen_names:
                seen_names.add(name)
                deduped_params.append(param)
        deduped_params.reverse()

        for param in deduped_params:
            param_name = param.get("name")
            param_in = param.get("in")

            if not param_name:
                continue

            if param_in == "path":
                path_params.append(param_name)
            elif param_in == "query":
                query_params.append(
                    {
                        "name": param_name,
                        "required": param.get("required", False),
                        "schema": param.get("schema", {}),
                        "description": param.get("description", ""),
                    }
                )

        # Build resource spec
        resource_spec = {
            "path": path,
            "operation_id": operation_id,
            "summary": get_op.get("summary", ""),
            "description": get_op.get("description", ""),
            "path_params": path_params,
            "query_params": query_params,
            "responses": get_op.get("responses", {}),
            "tags": tags,
        }

        # Group by primary tag
        if primary_tag not in resources_by_tag:
            resources_by_tag[primary_tag] = []
        resources_by_tag[primary_tag].append(resource_spec)

    return resources_by_tag
