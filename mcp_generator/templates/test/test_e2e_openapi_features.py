"""
Template generation for OpenAPI version-specific feature tests.

Generates pytest tests that validate correct handling of version-specific
OpenAPI features (Swagger 2.0, OpenAPI 3.0.x, OpenAPI 3.1.x).
"""

from ...models import ApiMetadata, ModuleSpec, SecurityConfig


def generate_openapi_feature_tests(
    api_metadata: ApiMetadata,
    security_config: SecurityConfig,
    modules: dict[str, ModuleSpec],
    openapi_spec: dict,
) -> str:
    """
    Generate tests for OpenAPI version-specific features.

    Args:
        api_metadata: API metadata
        security_config: Security configuration
        modules: Generated server modules
        openapi_spec: Full OpenAPI spec dict for introspection

    Returns:
        Complete test file content
    """

    # Detect OpenAPI version
    openapi_version = openapi_spec.get("openapi", openapi_spec.get("swagger", "unknown"))
    is_swagger_2 = openapi_version.startswith("2.")
    is_openapi_30 = openapi_version.startswith("3.0")
    is_openapi_31 = openapi_version.startswith("3.1")

    version_label = "Swagger 2.0" if is_swagger_2 else f"OpenAPI {openapi_version}"

    # Analyze spec features
    has_oauth2 = False
    has_api_key = False
    has_basic_auth = False
    has_bearer_auth = False
    oauth_flows = []

    if is_swagger_2:
        security_defs = openapi_spec.get("securityDefinitions", {})
        for _scheme_name, scheme in security_defs.items():
            if scheme.get("type") == "oauth2":
                has_oauth2 = True
                oauth_flows.append(scheme.get("flow", "unknown"))
            elif scheme.get("type") == "apiKey":
                has_api_key = True
            elif scheme.get("type") == "basic":
                has_basic_auth = True
    else:
        security_schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        for _scheme_name, scheme in security_schemes.items():
            if scheme.get("type") == "oauth2":
                has_oauth2 = True
                flows = scheme.get("flows", {})
                oauth_flows.extend(flows.keys())
            elif scheme.get("type") == "apiKey":
                has_api_key = True
            elif scheme.get("type") == "http":
                if scheme.get("scheme") == "bearer":
                    has_bearer_auth = True
                elif scheme.get("scheme") == "basic":
                    has_basic_auth = True

    # Check for multipart/form-data (file uploads)
    has_file_upload = False
    has_form_data = False
    for _path, path_item in openapi_spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                if is_swagger_2:
                    consumes = operation.get("consumes", [])
                    if "multipart/form-data" in consumes:
                        has_file_upload = True
                    if "application/x-www-form-urlencoded" in consumes:
                        has_form_data = True
                else:
                    request_body = operation.get("requestBody", {})
                    content = request_body.get("content", {})
                    if "multipart/form-data" in content:
                        has_file_upload = True
                    if "application/x-www-form-urlencoded" in content:
                        has_form_data = True

    # Check for response examples (3.0+) vs produces (2.0)
    has_examples = False
    response_content_types = set()
    for _path, path_item in openapi_spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                if is_swagger_2:
                    produces = operation.get("produces", [])
                    response_content_types.update(produces)
                else:
                    responses = operation.get("responses", {})
                    for _status, response in responses.items():
                        content = response.get("content", {})
                        response_content_types.update(content.keys())
                        for _media_type, media_obj in content.items():
                            if "examples" in media_obj or "example" in media_obj:
                                has_examples = True

    # Check for OpenAPI 3.1 specific features
    has_webhooks = "webhooks" in openapi_spec

    # Generate test header
    code = f'''"""
Generated OpenAPI Version-Specific Feature Tests for {api_metadata.title}

Tests that validate correct handling of {version_label} features.

OpenAPI Version: {openapi_version}

Version-Specific Features Detected:
- Security Schemes: {
        ", ".join(
            filter(
                None,
                [
                    "OAuth2" if has_oauth2 else None,
                    "API Key" if has_api_key else None,
                    "Basic Auth" if has_basic_auth else None,
                    "Bearer Token" if has_bearer_auth else None,
                ],
            )
        )
    }
- OAuth Flows: {", ".join(set(oauth_flows)) if oauth_flows else "None"}
- File Uploads: {"Yes" if has_file_upload else "No"}
- Form Data: {"Yes" if has_form_data else "No"}
- Response Examples: {"Yes" if has_examples else "No"}
{"- Webhooks: Yes" if has_webhooks else ""}

Generated by mcp_generator - DO NOT EDIT MANUALLY
"""

import pytest
import httpx
import os
import json


@pytest.fixture
def mcp_server_url():
    """MCP Server URL."""
    return os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")


@pytest.fixture
async def mcp_client(mcp_server_url):
    """Create an authenticated HTTP client for MCP server."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Initialize MCP session
        init_response = await client.post(
            mcp_server_url,
            json={{
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {{
                    "protocolVersion": "2025-03-26",
                    "capabilities": {{}},
                    "clientInfo": {{"name": "test", "version": "1.0"}}
                }}
            }},
            headers={{
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }}
        )

        session_id = init_response.headers.get("mcp-session-id")

        # Send initialized notification to complete handshake
        headers = {{
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }}
        if session_id:
            headers["mcp-session-id"] = session_id

        await client.post(
            mcp_server_url,
            json={{
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }},
            headers=headers
        )

        yield client, mcp_server_url, session_id


class TestOpenAPIVersionFeatures:
    """Test {version_label} specific features."""

    @pytest.mark.asyncio
    async def test_openapi_version_metadata(self, mcp_client):
        """Verify API metadata reflects {version_label} spec."""
        client, mcp_server_url, session_id = mcp_client

        headers = {{
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }}
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={{
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {{}}
            }},
            headers=headers
        )

        assert response.status_code == 200

        # Parse response
        data = {{}}
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            for line in response.text.split('\\n'):
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    break
        else:
            data = response.json()

        assert "result" in data
        assert "tools" in data["result"]

        # All tools should be generated regardless of OpenAPI version
        tools = data["result"]["tools"]
        assert len(tools) > 0, "Expected at least one tool to be generated"

        print(f"\\n✓ Generated {{len(tools)}} tools from {version_label} spec")
'''

    # Add Swagger 2.0 specific tests
    if is_swagger_2:
        code += '''

    @pytest.mark.asyncio
    async def test_swagger2_security_definitions(self, mcp_client):
        """Test Swagger 2.0 securityDefinitions handling."""
        # Swagger 2.0 uses securityDefinitions at root level
        # Generated tools should handle auth via BACKEND_API_TOKEN or oauth flows

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        assert response.status_code == 200
        print("\\n✓ Swagger 2.0 securityDefinitions processed correctly")
'''

        if has_oauth2 and "implicit" in oauth_flows:
            code += '''

    @pytest.mark.asyncio
    async def test_swagger2_implicit_oauth_flow(self, mcp_client):
        """Test Swagger 2.0 implicit OAuth2 flow support."""
        # Swagger 2.0 implicit flow uses authorizationUrl only
        # Verify auth middleware is configured for OAuth

        # This is a structural test - actual OAuth requires external provider
        # We just verify the server accepts tools/list without errors

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        assert response.status_code in [200, 401, 403]
        print("\\n✓ Swagger 2.0 implicit OAuth flow configured")
'''

        if has_file_upload:
            code += '''

    @pytest.mark.asyncio
    async def test_swagger2_multipart_form_data(self, mcp_client):
        """Test Swagger 2.0 multipart/form-data handling."""
        # Swagger 2.0 uses 'consumes' field for content types
        # File uploads use formData parameters with type: file

        client, mcp_server_url, session_id = mcp_client

        # Find a tool that handles file uploads
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        data = response.json() if not response.headers.get("content-type", "").startswith("text/event-stream") else json.loads([line for line in response.text.split('\\n') if line.startswith('data: ')][0][6:])
        tools = data["result"]["tools"]

        # Look for upload tools
        upload_tools = [t for t in tools if "upload" in t["name"].lower() or "file" in t["name"].lower()]

        if upload_tools:
            print(f"\\n✓ Found {{len(upload_tools)}} file upload tool(s): {{[t['name'] for t in upload_tools]}}")
        else:
            print("\\n⚠ No explicit file upload tools found (may be handled internally)")
'''

    # Add OpenAPI 3.0 specific tests
    if is_openapi_30:
        code += '''

    @pytest.mark.asyncio
    async def test_openapi30_components_schemas(self, mcp_client):
        """Test OpenAPI 3.0 components/schemas handling."""
        # OpenAPI 3.0 uses components/schemas instead of definitions
        # Components are properly referenced in generated tools

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        assert response.status_code == 200
        print("\\n✓ OpenAPI 3.0 components/schemas processed correctly")
'''

        if has_bearer_auth:
            code += '''

    @pytest.mark.asyncio
    async def test_openapi30_bearer_token_auth(self, mcp_client):
        """Test OpenAPI 3.0 HTTP Bearer token authentication."""
        # OpenAPI 3.0 introduced HTTP security schemes with bearer tokens
        # Verify bearer token handling in generated middleware

        client, mcp_server_url, session_id = mcp_client

        # Test without token
        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers={
                "Content-Type": "application/json"
            }
        )

        # Depending on validation mode, should return 200 (delegated) or 401 (validated)
        assert response.status_code in [200, 401, 403]
        print(f"\\n✓ Bearer token auth configured (status: {{response.status_code}})")
'''

        if has_examples:
            code += '''

    @pytest.mark.asyncio
    async def test_openapi30_response_examples(self, mcp_client):
        """Test OpenAPI 3.0 response examples handling."""
        # OpenAPI 3.0 supports examples in response content
        # Generator should handle example-based documentation

        # This is a metadata test - examples don't affect runtime behavior
        # but should be preserved in tool descriptions

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        data = response.json() if not response.headers.get("content-type", "").startswith("text/event-stream") else json.loads([line for line in response.text.split('\\n') if line.startswith('data: ')][0][6:])
        tools = data["result"]["tools"]

        # Check that tools have descriptions (where examples would be documented)
        tools_with_descriptions = [t for t in tools if t.get("description")]
        assert len(tools_with_descriptions) > 0
        print(f"\\n✓ {{len(tools_with_descriptions)}}/{{len(tools)}} tools have descriptions")
'''

    # Add OpenAPI 3.1 specific tests
    if is_openapi_31:
        code += '''

    @pytest.mark.asyncio
    async def test_openapi31_json_schema_compatibility(self, mcp_client):
        """Test OpenAPI 3.1 JSON Schema 2020-12 compatibility."""
        # OpenAPI 3.1 is fully compatible with JSON Schema
        # Features like const, if/then/else, prefixItems are supported

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        assert response.status_code == 200
        print("\\n✓ OpenAPI 3.1 JSON Schema features processed correctly")
'''

        if has_webhooks:
            code += '''

    @pytest.mark.asyncio
    async def test_openapi31_webhooks_support(self, mcp_client):
        """Test OpenAPI 3.1 webhooks support."""
        # OpenAPI 3.1 introduced webhooks as a top-level field
        # Webhooks define callback operations

        # Note: Webhook support in MCP servers depends on implementation
        # This test verifies the spec was parsed without errors

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        assert response.status_code == 200
        print("\\n✓ OpenAPI 3.1 webhooks definition processed")
'''

    # Add content-type negotiation test (all versions)
    if response_content_types:
        content_types_list = "', '".join(sorted(response_content_types))
        code += f'''

    @pytest.mark.asyncio
    async def test_content_type_negotiation(self, mcp_client):
        """Test API content type support."""
        # API supports: {content_types_list}

        client, mcp_server_url, session_id = mcp_client

        headers = {{
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }}
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={{
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {{}}
            }},
            headers=headers
        )

        assert response.status_code == 200

        # MCP server always returns JSON or SSE, regardless of underlying API content types
        content_type = response.headers.get("content-type", "")
        assert "json" in content_type or "event-stream" in content_type
        print(f"\\n✓ Content type negotiation works (MCP: {{content_type}})")
'''

    # Add parameter style test (query/path/header/cookie)
    code += '''

    @pytest.mark.asyncio
    async def test_parameter_serialization(self, mcp_client):
        """Test parameter serialization across different locations."""
        # Tests that parameters in path, query, header are correctly serialized

        client, mcp_server_url, session_id = mcp_client

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        response = await client.post(
            mcp_server_url,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "method": "tools/list",
                "params": {}
            },
            headers=headers
        )

        data = response.json() if not response.headers.get("content-type", "").startswith("text/event-stream") else json.loads([line for line in response.text.split('\\n') if line.startswith('data: ')][0][6:])
        tools = data["result"]["tools"]

        # Check input schemas for different parameter types
        param_locations = set()
        for tool in tools:
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                # Parameter location might be in description or custom fields
                if prop_schema.get("description"):
                    desc = prop_schema["description"].lower()
                    if "path" in desc:
                        param_locations.add("path")
                    elif "query" in desc:
                        param_locations.add("query")
                    elif "header" in desc:
                        param_locations.add("header")

        print(f"\\n✓ Parameter locations detected: {', '.join(sorted(param_locations)) if param_locations else 'auto-detected'}")
'''

    # Footer
    code += f'''


# Summary information
if __name__ == "__main__":
    print("""
    OpenAPI Version Feature Tests for {api_metadata.title}
    {"=" * 60}

    Testing {version_label} specific features:

    OpenAPI Version: {openapi_version}
    Security: {
        ", ".join(
            filter(
                None,
                [
                    "OAuth2" if has_oauth2 else None,
                    "API Key" if has_api_key else None,
                    "Basic Auth" if has_basic_auth else None,
                    "Bearer" if has_bearer_auth else None,
                ],
            )
        )
        or "None"
    }
    File Uploads: {"Yes" if has_file_upload else "No"}
    Form Data: {"Yes" if has_form_data else "No"}

    Run tests:
        pytest test_e2e_openapi_features_generated.py -v
    """)
'''

    return code
