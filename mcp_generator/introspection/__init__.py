"""
API introspection.

Split by extraction phase; re-exported here so importers keep one entry point.
"""

from .api import get_api_metadata, get_api_modules, get_security_config
from .body_schemas import _fields_to_coercion_schema, get_body_schemas
from .endpoints import get_delete_endpoints, get_display_endpoints, get_form_endpoints
from .resources import get_resource_endpoints
from .schema import (
    _extract_response_schema,
    _parse_schema_fields,
    _ref_cache,
    _resolve_ref,
)
from .spec import _load_openapi_spec, enrich_spec_tags

__all__ = [
    "_extract_response_schema",
    "_fields_to_coercion_schema",
    "_load_openapi_spec",
    "_parse_schema_fields",
    "_ref_cache",
    "_resolve_ref",
    "enrich_spec_tags",
    "get_api_metadata",
    "get_api_modules",
    "get_body_schemas",
    "get_delete_endpoints",
    "get_display_endpoints",
    "get_form_endpoints",
    "get_resource_endpoints",
    "get_security_config",
]
