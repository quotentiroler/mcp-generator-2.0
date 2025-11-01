"""
Test Generator - Generate authentication flow demonstration tests.

Generates comprehensive test files that demonstrate how to authenticate
and use the MCP server with different auth flows.
"""

import json
from pathlib import Path

from .models import ApiMetadata, ModuleSpec, SecurityConfig
from .templates.test_auth_flows import generate_auth_flow_tests as _generate_auth_flows
from .templates.test_tools import generate_tool_tests as _generate_tools


def _load_openapi_spec() -> dict:
    """Load the OpenAPI specification from openapi.json or openapi.yaml."""
    # First, try current working directory
    cwd = Path.cwd()
    search_dirs = [cwd, Path(__file__).parent.parent]
    for search_dir in search_dirs:
        for filename in ["openapi.json", "openapi.yaml", "openapi.yml"]:
            openapi_path = search_dir / filename
            if openapi_path.exists():
                try:
                    with open(openapi_path, encoding="utf-8") as f:
                        # Try JSON first
                        return json.load(f)
                except json.JSONDecodeError:
                    # Try YAML
                    try:
                        import yaml

                        with open(openapi_path, encoding="utf-8") as f:
                            return yaml.safe_load(f)
                    except Exception:
                        pass

    raise FileNotFoundError(
        f"OpenAPI spec not found in current working directory or at {Path(__file__).parent.parent / 'openapi.json'} or openapi.yaml"
    )


def _extract_oauth_flows_from_spec(openapi_spec: dict) -> set[str]:
    """
    Extract available OAuth2 flows from OpenAPI spec.

    Returns:
        Set of flow names: 'clientCredentials', 'authorizationCode', 'password', 'implicit'
    """
    flows = set()

    if "components" not in openapi_spec or "securitySchemes" not in openapi_spec["components"]:
        return flows

    for _scheme_name, scheme in openapi_spec["components"]["securitySchemes"].items():
        if scheme.get("type") == "oauth2" and "flows" in scheme:
            for flow_name in scheme["flows"].keys():
                # Convert to camelCase for consistency
                flows.add(flow_name)

    return flows


def _extract_client_examples_from_spec(openapi_spec: dict) -> list[dict[str, str]]:
    """
    Extract client examples from OpenAPI spec extensions.

    Looks for x-client-examples or similar extensions that document
    available OAuth clients for testing.

    Returns:
        List of dicts with 'client_id', 'client_secret', 'description'
    """
    clients = []

    # Check for custom extension with client examples
    if "x-client-examples" in openapi_spec:
        for client in openapi_spec["x-client-examples"]:
            clients.append(
                {
                    "client_id": client.get("clientId", ""),
                    "client_secret": client.get("clientSecret", ""),
                    "description": client.get("description", ""),
                    "grant_type": client.get("grantType", "client_credentials"),
                }
            )

    # Fallback to common examples if no spec extensions
    if not clients:
        clients.append(
            {
                "client_id": "admin-service",
                "client_secret": "admin-service-secret",
                "description": "Admin service account for testing",
                "grant_type": "client_credentials",
            }
        )

    return clients


def generate_auth_flow_tests(
    api_metadata: ApiMetadata, security_config: SecurityConfig, modules: dict[str, ModuleSpec]
) -> str:
    """Generate tests demonstrating authentication flows.

    Args:
        api_metadata: API metadata
        security_config: Security configuration
        modules: Generated server modules

    Returns:
        str: Complete test file content
    """

    # Load OpenAPI spec to get accurate OAuth flow information
    try:
        openapi_spec = _load_openapi_spec()
        available_flows = _extract_oauth_flows_from_spec(openapi_spec)
    except Exception as e:
        print(f"Warning: Could not load OpenAPI spec: {e}")
        available_flows = set()

    # Use template to generate test code
    return _generate_auth_flows(api_metadata, security_config, modules, available_flows)


def generate_tool_tests(
    modules: dict[str, ModuleSpec], api_metadata: ApiMetadata, security_config: SecurityConfig
) -> str:
    """Generate basic tests for tool validation.

    Args:
        modules: Generated server modules
        api_metadata: API metadata
        security_config: Security configuration

    Returns:
        str: Test file content for tool validation
    """

    # Use template to generate test code
    return _generate_tools(modules, api_metadata, security_config)


def generate_test_runner(api_metadata: ApiMetadata, server_name: str) -> str:
    """Generate test runner script that starts server and runs tests.

    Args:
        api_metadata: API metadata for title and description
        server_name: Name of the generated server script (without .py extension)

    Returns:
        str: Test runner script content
    """
    from .templates.test_runner import generate_test_runner as _generate_runner

    return _generate_runner(api_metadata, server_name)
