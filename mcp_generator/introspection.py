"""
API introspection utilities.

Handles discovery and introspection of generated API client classes,
extraction of metadata from OpenAPI specs, and security configuration parsing.
"""

import json
import sys
from pathlib import Path
from typing import Any

from .models import ApiMetadata, OAuthConfig, OAuthFlowConfig, SecurityConfig
from .utils import camel_to_snake


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
            return json.load(f)
    except json.JSONDecodeError:
        # If JSON fails, try YAML
        try:
            import yaml

            with open(spec_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
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
                additional_metadata["servers"] = spec.get("servers", [])
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

    # Extract security schemes from components
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})

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

    config.default_scopes = sorted(default_scopes) if default_scopes else ["backend:read"]

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

    resources_by_tag = {}

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

        for param in get_op.get("parameters", []):
            param_name = param.get("name")
            param_in = param.get("in")

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
