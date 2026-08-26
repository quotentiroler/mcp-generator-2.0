"""
API introspection utilities.

Handles discovery and introspection of generated API client classes,
extraction of metadata from OpenAPI specs, and security configuration parsing.
"""

import json
import sys
from pathlib import Path
from typing import Any

from .config import DEFAULT_FALLBACK_SCOPES
from .models import (
    ApiMetadata,
    DeleteEndpoint,
    DisplayEndpoint,
    FormEndpoint,
    OAuthConfig,
    OAuthFlowConfig,
    ResponseField,
    ResponseSchema,
    SecurityConfig,
)
from .utils import camel_to_snake


def enrich_spec_tags(spec: dict[str, Any]) -> list[str]:
    """
    Auto-discover tags from endpoint definitions and add undeclared ones to the
    top-level ``tags`` array.

    The OpenAPI specification allows endpoints to reference tags that are not
    declared in the top-level ``tags`` list.  Some frameworks (e.g. Elysia)
    silently drop tags from the top-level list even though they are used on
    operations.  The openapi-generator-cli and downstream tooling may rely on
    declared tags to generate API classes, so we must ensure every tag in use is
    declared.

    Args:
        spec: Parsed OpenAPI specification (modified **in-place**).

    Returns:
        List of tag names that were auto-discovered and added.
    """
    declared_tags: set[str] = {t["name"] for t in spec.get("tags", [])}

    # Scan all operations for tags that are used but not declared
    discovered: list[str] = []
    for _path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "put", "post", "delete", "patch", "options", "head", "trace"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            for tag in operation.get("tags", []):
                if tag not in declared_tags:
                    spec.setdefault("tags", []).append(
                        {"name": tag, "description": "Auto-discovered from endpoint definitions"}
                    )
                    declared_tags.add(tag)
                    discovered.append(tag)

    return discovered


def _load_openapi_spec(spec_path: Path) -> dict[str, Any] | None:
    """
    Load OpenAPI specification from either JSON or YAML format.

    Args:
        spec_path: Path to the OpenAPI specification file

    Returns:
        Parsed OpenAPI spec as a dictionary, or None if loading fails
    """
    if not spec_path.exists():
        return None

    try:
        # Try loading as JSON first
        with open(spec_path, encoding="utf-8") as f:
            return dict(json.load(f))
    except json.JSONDecodeError:
        # If JSON fails, try YAML
        try:
            import yaml

            with open(spec_path, encoding="utf-8") as f:
                return dict(yaml.safe_load(f))
        except ImportError:
            print("   ⚠️  Could not load YAML file (PyYAML not installed)")
            print("   💡 Install with: pip install pyyaml")
            return None
        except Exception as e:
            print(f"   ⚠️  Could not parse OpenAPI spec as YAML: {e}")
            return None
    except Exception as e:
        print(f"   ⚠️  Could not load OpenAPI spec: {e}")
        return None


def _find_openapi_spec(base_dir: Path | None = None) -> Path | None:
    """Find the OpenAPI specification file (supports both .json and .yaml extensions).

    Args:
        base_dir: Base directory to search for openapi files. Defaults to current working directory.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Try openapi.json first (most common)
    json_path = base_dir / "openapi.json"
    if json_path.exists():
        return json_path

    # Try openapi.yaml
    yaml_path = base_dir / "openapi.yaml"
    if yaml_path.exists():
        return yaml_path

    # Try openapi.yml
    yml_path = base_dir / "openapi.yml"
    if yml_path.exists():
        return yml_path

    return None


def get_api_modules(base_dir: Path | None = None) -> dict[str, type]:
    """Import all API modules from the generated client dynamically.

    Args:
        base_dir: Base directory containing generated_openapi. Defaults to current working directory.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Add generated folder to path (so we can import openapi_client as a package)
    generated_path = base_dir / "generated_openapi"
    if str(generated_path) not in sys.path:
        sys.path.insert(0, str(generated_path))

    # Import the openapi_client package
    import openapi_client

    # Dynamically discover all API classes (classes ending with 'Api')
    api_modules = {}

    for name in dir(openapi_client):
        if name.endswith("Api") and not name.startswith("_"):
            api_class = getattr(openapi_client, name)

            # Verify it's actually a class (not a module or other object)
            if isinstance(api_class, type):
                # Convert class name to snake_case variable name
                # e.g., HealthcareUsersApi -> healthcare_users_api
                var_name = camel_to_snake(name)
                api_modules[var_name] = api_class

    return api_modules


def get_api_metadata(base_dir: Path | None = None) -> ApiMetadata:
    """Extract comprehensive API metadata from the generated client and OpenAPI spec.

    Args:
        base_dir: Base directory containing generated_openapi. Defaults to current working directory.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Add generated folder to path
    generated_path = base_dir / "generated_openapi"
    if str(generated_path) not in sys.path:
        sys.path.insert(0, str(generated_path))

    try:
        import openapi_client

        # Extract basic metadata from the generated client's docstring
        api_title = "Generated API"
        api_description = ""

        if openapi_client.__doc__:
            lines = [
                line.strip() for line in openapi_client.__doc__.strip().split("\n") if line.strip()
            ]
            # First non-empty line is typically the API title
            api_title = lines[0] if lines else "Generated API"
            # Second line is typically the description
            api_description = lines[1] if len(lines) > 1 else ""

        # Get version
        api_version = getattr(openapi_client, "__version__", "0.0.1")

        # Try to load OpenAPI spec for additional metadata
        openapi_path = _find_openapi_spec(base_dir)
        additional_metadata = {}

        if openapi_path and openapi_path.exists():
            spec = _load_openapi_spec(openapi_path)

            if spec:
                # Auto-discover tags from endpoint definitions before
                # reading the top-level tags list.  This ensures tags that
                # are used on operations but not declared at the top level
                # are included in the metadata (and downstream generation).
                discovered = enrich_spec_tags(spec)
                if discovered:
                    print(
                        f"   🏷️  Auto-discovered {len(discovered)} undeclared tag(s): {', '.join(discovered)}"
                    )

                # Extract info object fields
                info = spec.get("info", {})
                if info.get("title"):
                    api_title = info["title"]
                if info.get("description"):
                    api_description = info["description"]
                if info.get("version"):
                    api_version = info["version"]

                additional_metadata["contact"] = info.get("contact", {})
                additional_metadata["license"] = info.get("license", {})
                additional_metadata["terms_of_service"] = info.get("termsOfService")

                # Build servers list: OpenAPI 3.x uses "servers", Swagger 2.0 uses host/basePath/schemes
                servers = spec.get("servers", [])
                if not servers and spec.get("host"):
                    scheme = (spec.get("schemes") or ["https"])[0]
                    base_path = spec.get("basePath", "")
                    servers = [{"url": f"{scheme}://{spec['host']}{base_path}"}]
                additional_metadata["servers"] = servers

                additional_metadata["external_docs"] = spec.get("externalDocs", {})
                additional_metadata["tags"] = spec.get("tags", [])

                # Extract icon/logo from OpenAPI extensions
                # Check for x-logo (Redoc convention)
                if "x-logo" in info:
                    logo_config = info["x-logo"]
                    if isinstance(logo_config, dict):
                        additional_metadata["icon_url"] = logo_config.get("url")
                    elif isinstance(logo_config, str):
                        additional_metadata["icon_url"] = logo_config

                # Check for x-icon (alternative convention)
                if "x-icon" in info and not additional_metadata.get("icon_url"):
                    additional_metadata["icon_url"] = info["x-icon"]

                # Check for x-icon-emoji
                if "x-icon-emoji" in info:
                    additional_metadata["icon_emoji"] = info["x-icon-emoji"]

        return ApiMetadata(
            title=api_title, description=api_description, version=api_version, **additional_metadata
        )
    except Exception:
        # Fallback if metadata extraction fails
        return ApiMetadata()


def get_security_config(base_dir: Path | None = None) -> SecurityConfig:
    """Extract security configuration from OpenAPI spec.

    Args:
        base_dir: Base directory containing openapi files. Defaults to current working directory.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    openapi_path = _find_openapi_spec(base_dir)

    if not openapi_path or not openapi_path.exists():
        print("   ⚠️  OpenAPI spec not found")
        print("   💡 Run: bun run backend/src/export-openapi.ts")
        print("   Using default security configuration")
        return SecurityConfig()

    print(f"   📄 Reading OpenAPI spec from: {openapi_path}")

    spec = _load_openapi_spec(openapi_path)

    if not spec:
        print("   ⚠️  Could not parse OpenAPI spec")
        print("   Using default security configuration")
        return SecurityConfig()

    # Extract security schemes from components (OpenAPI 3.x) or securityDefinitions (Swagger 2.0)
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})

    # Swagger 2.0 fallback
    if not security_schemes:
        security_schemes = spec.get("securityDefinitions", {})

    if not security_schemes:
        return SecurityConfig()

    config = SecurityConfig(schemes=security_schemes, global_security=spec.get("security", []))

    # Extract OAuth2 configuration if present
    for scheme_name, scheme_def in security_schemes.items():
        scheme_type = scheme_def.get("type", "").lower()

        if scheme_type == "oauth2":
            flows = scheme_def.get("flows", {})
            oauth_config = OAuthConfig(scheme_name=scheme_name)

            # Extract all OAuth flows
            for flow_type in ["authorizationCode", "implicit", "password", "clientCredentials"]:
                if flow_type in flows:
                    flow_def = flows[flow_type]
                    oauth_flow = OAuthFlowConfig(
                        authorization_url=flow_def.get("authorizationUrl"),
                        token_url=flow_def.get("tokenUrl"),
                        refresh_url=flow_def.get("refreshUrl"),
                        scopes=flow_def.get("scopes", {}),
                    )
                    oauth_config.flows[flow_type] = oauth_flow
                    # Collect all scopes
                    oauth_config.all_scopes.update(flow_def.get("scopes", {}))

            config.oauth_config = oauth_config

        elif scheme_type == "http" and scheme_def.get("scheme") == "bearer":
            # Bearer token (JWT)
            config.bearer_format = scheme_def.get("bearerFormat", "JWT")

    # Extract default scopes from global security requirements
    default_scopes = set()
    for sec_req in config.global_security:
        for _scheme_name, scopes in sec_req.items():
            default_scopes.update(scopes)

    config.default_scopes = (
        sorted(default_scopes) if default_scopes else list(DEFAULT_FALLBACK_SCOPES)
    )

    # Extract OpenAPI extensions for additional auth config
    if "x-jwks-uri" in spec:
        config.jwks_uri = spec["x-jwks-uri"]
    if "x-issuer" in spec:
        config.issuer = spec["x-issuer"]
    if "x-audience" in spec:
        config.audience = spec["x-audience"]

    return config


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
