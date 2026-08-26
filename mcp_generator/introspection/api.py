"""Extracts API modules, metadata and security config from the spec and client."""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import DEFAULT_FALLBACK_SCOPES
from ..models import (
    ApiMetadata,
    OAuthConfig,
    OAuthFlowConfig,
    SecurityConfig,
)
from ..utils import camel_to_snake
from .spec import _find_openapi_spec, _load_openapi_spec, enrich_spec_tags


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
