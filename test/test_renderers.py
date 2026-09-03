"""Tests for mcp_generator.renderers — code generation output validation."""

import pytest

from mcp_generator.fastmcp_target import resolve_target
from mcp_generator.models import ApiMetadata, OAuthConfig, OAuthFlowConfig, SecurityConfig
from mcp_generator.renderers import (
    generate_tool_for_method,
    render_fastmcp_template,
    render_pyproject_template,
)

# ---------------------------------------------------------------------------
# render_pyproject_template
# ---------------------------------------------------------------------------


class TestRenderPyprojectTemplate:
    def test_contains_default_fastmcp_dep(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=5
        )
        assert "fastmcp>=4.0.2,<5.0.0" in content

    def test_does_not_contain_fastmcp_2x_dep(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=5
        )
        assert "fastmcp>=2" not in content

    def test_project_name_sanitized(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "my_cool.api", total_tools=1
        )
        assert 'name = "my-cool-api"' in content

    def test_version_sanitized(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        # Modify api_metadata version to trigger sanitization
        api_metadata.version = "1.0.0.abc123"
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1
        )
        # The version in pyproject should have '+' instead of final '.'
        assert "1.0.0+abc123" in content

    def test_middleware_package_included_when_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_bearer, "test_api", total_tools=1
        )
        # Python list repr uses single quotes: ['servers', 'middleware']
        assert "'middleware'" in content

    def test_storage_dep_when_enabled(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1, enable_storage=True
        )
        assert "cryptography" in content

    def test_apps_dep_when_enabled(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1, enable_apps=True
        )
        assert "fastmcp[apps]>=4.0.2,<5.0.0" in content

    def test_apps_dep_not_present_when_disabled(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1
        )
        assert "fastmcp[apps]" not in content

    def test_apps_package_included_when_enabled(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1, enable_apps=True
        )
        assert "'apps'" in content


# ---------------------------------------------------------------------------
# render_fastmcp_template
# ---------------------------------------------------------------------------


class TestRenderFastmcpTemplate:
    def test_returns_valid_json(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert "composition" in parsed or isinstance(parsed, dict)

    def test_strategy_is_mount(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        assert '"mount"' in content

    def test_features_section_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert "features" in parsed

    def test_feature_keys_complete(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """All 11 FastMCP 3.0/3.1 feature keys exist in the template."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        expected_keys = {
            "tool_tags",
            "tool_timeouts",
            "search_tools",
            "code_mode",
            "response_limiting",
            "ping_middleware",
            "rate_limiting",
            "multi_auth",
            "component_versioning",
            "validate_output",
            "dynamic_visibility",
            "opentelemetry",
            "oauth_proxy",
        }
        assert expected_keys.issubset(set(features.keys()))

    def test_version_filter_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """version_filter key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "version_filter" in features
        vf = features["version_filter"]
        assert "enabled" in vf
        assert "include_unversioned" in vf
        assert "version_gte" in vf
        assert "version_lt" in vf

    def test_propelauth_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """propelauth key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "propelauth" in features
        pa = features["propelauth"]
        assert "enabled" in pa
        assert "auth_url" in pa
        assert "introspection_client_id" in pa
        assert "introspection_client_secret" in pa

    def test_search_tools_serializer_field(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """search_tools should have a serializer field."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        search = json.loads(content)["features"]["search_tools"]
        assert "serializer" in search

    def test_version_filter_defaults(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """version_filter should default to disabled with include_unversioned=true."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        vf = json.loads(content)["features"]["version_filter"]
        assert vf["enabled"] is False
        assert vf["include_unversioned"] is True

    def test_opentelemetry_service_name_rendered(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """service_name placeholder should be replaced with API title."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        otel = json.loads(content)["features"]["opentelemetry"]
        assert "{{service_name}}" not in otel.get("service_name", "")
        assert api_metadata.title.lower().replace(" ", "-") in otel["service_name"]

    def test_telemetry_optional_dep_in_pyproject(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1
        )
        assert "opentelemetry-api" in content
        assert "opentelemetry-sdk" in content

    def test_rate_limiting_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """rate_limiting key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "rate_limiting" in features
        rl = features["rate_limiting"]
        assert "enabled" in rl
        assert "max_requests_per_second" in rl
        assert "burst_capacity" in rl
        assert "global_limit" in rl

    def test_oauth_proxy_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """oauth_proxy key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "oauth_proxy" in features
        op = features["oauth_proxy"]
        assert "enabled" in op
        assert "upstream_authorization_endpoint" in op
        assert "upstream_token_endpoint" in op
        assert "upstream_client_id" in op
        assert "upstream_client_secret" in op
        assert "forward_pkce" in op

    def test_no_auth_validate_tokens_false(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """When no auth is configured, validate_tokens should be false."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert parsed["middleware"]["config"]["authentication"]["validate_tokens"] is False

    def test_bearer_only_validate_tokens_true(
        self, api_metadata: ApiMetadata, sample_modules: dict
    ) -> None:
        """When bearer auth is configured (no authorizationCode flow), validate_tokens should be true."""
        import json

        sc = SecurityConfig(
            schemes={"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
            bearer_format="JWT",
        )
        content = render_fastmcp_template(
            api_metadata, sc, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert parsed["middleware"]["config"]["authentication"]["validate_tokens"] is True
        assert parsed["features"]["oauth_proxy"]["enabled"] is False

    def test_oauth_authorization_code_enables_proxy(
        self, api_metadata: ApiMetadata, sample_modules: dict
    ) -> None:
        """When an authorizationCode flow is detected, oauth_proxy should be auto-populated."""
        import json

        sc = SecurityConfig(
            schemes={"oauth2": {"type": "oauth2"}},
            oauth_config=OAuthConfig(
                scheme_name="oauth2",
                flows={
                    "authorizationCode": OAuthFlowConfig(
                        authorization_url="https://auth.example.com/authorize",
                        token_url="https://auth.example.com/token",
                        scopes={"read": "Read access", "write": "Write access"},
                    )
                },
                all_scopes={"read": "Read access", "write": "Write access"},
            ),
        )
        content = render_fastmcp_template(
            api_metadata, sc, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        oauth_proxy = parsed["features"]["oauth_proxy"]
        assert oauth_proxy["enabled"] is True
        assert (
            oauth_proxy["upstream_authorization_endpoint"] == "https://auth.example.com/authorize"
        )
        assert oauth_proxy["upstream_token_endpoint"] == "https://auth.example.com/token"
        assert set(oauth_proxy["valid_scopes"]) == {"read", "write"}
        assert parsed["middleware"]["config"]["authentication"]["validate_tokens"] is True

    def test_oauth_client_credentials_no_proxy(
        self,
        api_metadata: ApiMetadata,
        security_config_bearer: SecurityConfig,
        sample_modules: dict,
    ) -> None:
        """clientCredentials flow should NOT enable oauth_proxy (only authorizationCode does)."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_bearer, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert parsed["features"]["oauth_proxy"]["enabled"] is False
        # But validate_tokens should still be true since auth schemes exist
        assert parsed["middleware"]["config"]["authentication"]["validate_tokens"] is True

    def test_apikey_only_validate_tokens_false(
        self, api_metadata: ApiMetadata, sample_modules: dict
    ) -> None:
        """apiKey-only auth should NOT enable validate_tokens (no JWT to validate)."""
        import json

        sc = SecurityConfig(
            schemes={"api_key": {"type": "apiKey", "name": "api_key", "in": "header"}},
        )
        content = render_fastmcp_template(
            api_metadata, sc, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert parsed["middleware"]["config"]["authentication"]["validate_tokens"] is False
        assert parsed["features"]["oauth_proxy"]["enabled"] is False

    # --- MCP Apps feature ---

    def test_apps_section_present_by_default(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """Apps section should be present in features by default."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "apps" in features
        apps = features["apps"]
        assert "enabled" in apps
        assert "display_tools" in apps
        assert "generative_ui" in apps

    def test_apps_disabled_by_default(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """Apps should be disabled when enable_apps is not set."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        apps = json.loads(content)["features"]["apps"]
        assert apps["enabled"] is False

    def test_apps_enabled_when_flag_set(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """Apps should be enabled when enable_apps=True."""
        import json

        content = render_fastmcp_template(
            api_metadata,
            security_config_none,
            sample_modules,
            total_tools=5,
            server_name="test",
            enable_apps=True,
        )
        apps = json.loads(content)["features"]["apps"]
        assert apps["enabled"] is True

    def test_apps_generative_ui_default_false(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """generative_ui should default to false even when apps is enabled."""
        import json

        content = render_fastmcp_template(
            api_metadata,
            security_config_none,
            sample_modules,
            total_tools=5,
            server_name="test",
            enable_apps=True,
        )
        apps = json.loads(content)["features"]["apps"]
        assert apps["generative_ui"] is False


# ---------------------------------------------------------------------------
# Generated tool code — progress, elicitation, sampling (FastMCP 3.1)
# ---------------------------------------------------------------------------


class TestGeneratedToolFeatures:
    """Test that generated tool functions include new FastMCP features."""

    @pytest.fixture
    def tool_code(self) -> str:
        """Generate a tool function from a simple API method."""

        def get_pet(pet_id: str) -> dict:
            """Get a pet by ID."""
            return {}

        return generate_tool_for_method("pet_api", "get_pet", get_pet, tag_name="pet")

    @pytest.fixture
    def tool_code_v3(self) -> str:
        """Same tool pinned to FastMCP 3, which still has elicit and sample."""

        def get_pet(pet_id: str) -> dict:
            """Get a pet by ID."""
            return {}

        return generate_tool_for_method(
            "pet_api", "get_pet", get_pet, tag_name="pet", target=resolve_target(3)
        )

    @pytest.fixture
    def tool_code_required_params(self) -> str:
        """Generate a tool with required parameters for elicitation testing."""

        def add_pet(name: str, status: str) -> dict:
            """Add a new pet."""
            return {}

        return generate_tool_for_method("pet_api", "add_pet", add_pet, tag_name="pet")

    @pytest.fixture
    def tool_code_required_params_v3(self) -> str:
        """Same tool pinned to FastMCP 3, whose missing-param path elicits."""

        def add_pet(name: str, status: str) -> dict:
            """Add a new pet."""
            return {}

        return generate_tool_for_method(
            "pet_api", "add_pet", add_pet, tag_name="pet", target=resolve_target(3)
        )

    def test_progress_reporting_start(self, tool_code: str) -> None:
        """Tools should report progress at start."""
        assert "report_progress(0, 3" in tool_code

    def test_progress_reporting_api_call(self, tool_code: str) -> None:
        """Tools should report progress when calling API."""
        assert "report_progress(1, 3" in tool_code

    def test_progress_reporting_done(self, tool_code: str) -> None:
        """Tools should report progress on completion."""
        assert "report_progress(3, 3" in tool_code

    def test_elicitation_for_missing_params(self, tool_code_required_params_v3: str) -> None:
        """FastMCP 3 asks the client for missing required params."""
        assert "ctx.elicit(" in tool_code_required_params_v3

    def test_elicitation_uses_response_type(self, tool_code_required_params_v3: str) -> None:
        """Elicitation should use response_type=str (FastMCP 3.2.4+)."""
        assert "response_type=str" in tool_code_required_params_v3

    def test_elicitation_checks_missing(self, tool_code_required_params: str) -> None:
        """Elicitation should check for missing required parameters."""
        assert "_missing" in tool_code_required_params
        assert "_required" in tool_code_required_params

    def test_elicitation_handles_decline(self, tool_code_required_params_v3: str) -> None:
        """Elicitation should handle user declining."""
        assert "accept" in tool_code_required_params_v3

    def test_elicitation_graceful_fallback(self, tool_code_v3: str) -> None:
        """Elicitation should not fail if client doesn't support it."""
        assert "pass  # Elicitation not supported" in tool_code_v3

    def test_sampling_on_api_error(self, tool_code_v3: str) -> None:
        """Tools should use ctx.sample() for LLM-assisted error recovery on API errors."""
        assert "ctx.sample(" in tool_code_v3

    def test_sampling_suggestion_in_error(self, tool_code_v3: str) -> None:
        """Sampling result should be included in the error message as a suggestion."""
        assert "Suggestion" in tool_code_v3

    def test_default_target_reports_missing_params_instead_of_eliciting(
        self, tool_code_required_params: str
    ) -> None:
        """FastMCP 4 cannot elicit to a default client, so the tool reports back."""
        assert "ctx.elicit(" not in tool_code_required_params
        assert "missing_required_parameters" in tool_code_required_params

    def test_default_target_has_no_server_sampling(self, tool_code: str) -> None:
        """ctx.sample is removed from the FastMCP 4 server API."""
        assert "ctx.sample(" not in tool_code

    def test_sampling_fallback_on_failure(self, tool_code: str) -> None:
        """If sampling fails, tool should still raise the original API error."""
        assert "API Error:" in tool_code


# ---------------------------------------------------------------------------
# Body schema coercion in generated tools
# ---------------------------------------------------------------------------


class TestBodySchemaCoercion:
    """Verify that body_schemas inject _coerce_form_data into generated modules."""

    def _make_method(self) -> type:
        """Create a fake API class with a method that has a 'body' parameter."""

        class FakeApi:
            def add_pet(self, body: str, **kwargs) -> object:  # noqa: D102
                """Add a new pet to the store."""

        return FakeApi

    def test_coerce_function_generated_when_schema_present(self) -> None:
        from mcp_generator.renderers import generate_server_module

        FakeApi = self._make_method()
        schemas = {
            "add_pet": {
                "name": {"type": "string"},
                "category": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        }
        module = generate_server_module("pet_api", FakeApi, body_schemas=schemas)
        assert "def _coerce_form_data(" in module.code

    def test_coerce_function_absent_when_no_schemas(self) -> None:
        from mcp_generator.renderers import generate_server_module

        FakeApi = self._make_method()
        module = generate_server_module("pet_api", FakeApi, body_schemas=None)
        assert "_coerce_form_data" not in module.code

    def test_body_schema_literal_embedded_in_tool(self) -> None:
        from mcp_generator.renderers import generate_tool_for_method

        FakeApi = self._make_method()
        schemas = {
            "add_pet": {
                "name": {"type": "string"},
                "photoUrls": {"type": "array", "items": {"type": "string"}},
            }
        }
        code = generate_tool_for_method("pet_api", "add_pet", FakeApi.add_pet, body_schemas=schemas)
        assert "_body_schema" in code
        assert "_coerce_form_data(data, _body_schema)" in code
        assert "'photoUrls'" in code

    def test_plain_json_dumps_when_no_schema_for_method(self) -> None:
        from mcp_generator.renderers import generate_tool_for_method

        FakeApi = self._make_method()
        # body_schemas exists but doesn't have an entry for add_pet
        schemas = {"update_pet": {"name": {"type": "string"}}}
        code = generate_tool_for_method("pet_api", "add_pet", FakeApi.add_pet, body_schemas=schemas)
        assert "_coerce_form_data" not in code
        assert "_json.dumps(data)" in code

    def test_coerce_function_reshapes_flat_data(self) -> None:
        """Execute the generated _coerce_form_data function to verify runtime behavior."""
        from mcp_generator.renderers import generate_server_module

        FakeApi = self._make_method()
        schemas = {
            "add_pet": {
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
                        "properties": {"name": {"type": "string"}},
                    },
                },
                "status": {"type": "string", "enum": ["available", "pending", "sold"]},
            }
        }
        module = generate_server_module("pet_api", FakeApi, body_schemas=schemas)
        # Extract just the _coerce_form_data function from the generated code
        # (the full module imports openapi_client which isn't available in tests)
        lines = module.code.split("\n")
        func_start = None
        func_end = None
        for i, line in enumerate(lines):
            if line.startswith("def _coerce_form_data("):
                func_start = i
            elif (
                func_start is not None
                and line != ""
                and not line.startswith(" ")
                and i > func_start + 1
            ):
                func_end = i
                break
        assert func_start is not None, "_coerce_form_data not found in generated code"
        if func_end is None:
            func_end = len(lines)
        func_code = "\n".join(lines[func_start:func_end])
        ns: dict = {}
        exec(compile(func_code, "<test>", "exec"), ns)  # noqa: S102
        coerce = ns["_coerce_form_data"]

        flat = {
            "name": "Buddy",
            "category": "Dogs",
            "photoUrls": "https://example.com/photo.jpg",
            "tags": "friendly, cute",
            "status": "available",
        }
        result = coerce(flat, schemas["add_pet"])

        assert result["name"] == "Buddy"
        assert result["status"] == "available"
        assert result["category"] == {"name": "Dogs"}
        assert result["photoUrls"] == ["https://example.com/photo.jpg"]
        assert result["tags"] == [{"name": "friendly"}, {"name": "cute"}]
