"""Builds request-body coercion schemas for flat-to-nested form data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import (
    ResponseField,
)
from ..utils import camel_to_snake
from .endpoints import _extract_request_body_schema
from .spec import _find_openapi_spec, _load_openapi_spec


def _fields_to_coercion_schema(fields: list[ResponseField]) -> dict[str, Any]:
    """Convert ResponseField list into a simplified schema dict for code generation.

    The returned dict maps field names to type descriptors that the runtime
    ``_coerce_form_data`` function uses to reshape flat form values into the
    structure the API expects.

    Example output for the Petstore ``Pet`` schema::

        {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "category": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            },
            "photoUrls": {"type": "array", "items": {"type": "string"}},
            "tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                },
            },
            "status": {"type": "string", "enum": ["available", "pending", "sold"]},
        }
    """
    _PYTHON_TO_JSON_TYPE = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}
    schema: dict[str, Any] = {}
    for f in fields:
        if f.is_array:
            item_desc: dict[str, Any]
            if f.nested_fields:
                item_desc = {
                    "type": "object",
                    "properties": _fields_to_coercion_schema(f.nested_fields),
                }
            else:
                item_desc = {"type": _PYTHON_TO_JSON_TYPE.get(f.python_type, "string")}
            schema[f.name] = {"type": "array", "items": item_desc}
        elif f.is_nested_object and f.nested_fields:
            schema[f.name] = {
                "type": "object",
                "properties": _fields_to_coercion_schema(f.nested_fields),
            }
        else:
            entry: dict[str, Any] = {"type": _PYTHON_TO_JSON_TYPE.get(f.python_type, "string")}
            if f.is_enum and f.enum_values:
                entry["enum"] = f.enum_values
            schema[f.name] = entry
    return schema


def get_body_schemas(base_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Extract request body schemas for POST/PUT operations.

    Returns a dictionary mapping ``snake_case_method_name`` → simplified body
    schema dict.  The schema is consumed at code-generation time and embedded
    as a literal in the generated server module so that the runtime
    ``_coerce_form_data`` helper can reshape flat form data into the nested
    structure the API expects.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    openapi_path = _find_openapi_spec(base_dir)
    if not openapi_path or not openapi_path.exists():
        return {}

    spec = _load_openapi_spec(openapi_path)
    if not spec or "paths" not in spec:
        return {}

    schemas: dict[str, dict[str, Any]] = {}
    for _path, path_item in spec.get("paths", {}).items():
        for method in ("post", "put", "patch"):
            if method not in path_item:
                continue
            op = path_item[method]
            operation_id = op.get("operationId")
            if not operation_id:
                continue

            result = _extract_request_body_schema(op, spec)
            if result is None:
                continue

            _schema_name, fields, _required = result
            # Key by snake_case method name — matches the method name used
            # by _build_tool_spec → sanitize_name → tool_name
            method_name = camel_to_snake(operation_id)
            schemas[method_name] = _fields_to_coercion_schema(fields)

    return schemas
