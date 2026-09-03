"""Tests for mcp_generator.generator — composition server generation."""

from pathlib import Path

import pytest

from mcp_generator.generator import generate_main_composition_server
from mcp_generator.models import ApiMetadata, ModuleSpec, SecurityConfig

# ---------------------------------------------------------------------------
# Fixtures (local to this module — also re-uses conftest fixtures)
# ---------------------------------------------------------------------------


@pytest.fixture
def _two_modules() -> dict[str, ModuleSpec]:
    return {
        "pet": ModuleSpec(
            filename="pet_server.py",
            api_var_name="pet_api",
            api_class_name="PetApi",
            module_name="pet",
            tool_count=3,
            code="",
        ),
        "store": ModuleSpec(
            filename="store_server.py",
            api_var_name="store_api",
            api_class_name="StoreApi",
            module_name="store",
            tool_count=4,
            code="",
        ),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateMainCompositionServer:
    """Test the main composition server code generation ."""

    def test_returns_string(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert isinstance(code, str)
        assert len(code) > 200

    # --- FastMCP API usage ---

    def test_uses_mount_namespace(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert 'mount(pet_mcp, namespace="pet")' in code
        assert 'mount(store_mcp, namespace="store")' in code

    def test_does_not_use_deprecated_import_server(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "import_server" not in code

    def test_does_not_use_mount_prefix(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "prefix=" not in code

    def test_does_not_use_resource_prefix_format(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "resource_prefix_format" not in code

    def test_uses_app_run_transport(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert 'app.run(transport="stdio")' in code
        assert 'app.run(transport="http"' in code

    def test_uses_http_app_not_create_streamable(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "app.http_app(" in code
        assert "create_streamable_http_app" not in code

    def test_uses_fastmcp_event_store(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "from fastmcp.server.event_store import EventStore" in code

    # --- Header / metadata ---

    def test_header_contains_title(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert api_metadata.title in code

    def test_header_contains_version(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert api_metadata.version in code

    def test_contact_included_when_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "test@example.com" in code

    def test_contact_absent_when_not_set(
        self,
        api_metadata_no_extras: ApiMetadata,
        security_config_none: SecurityConfig,
        _two_modules: dict,
    ) -> None:
        code = generate_main_composition_server(
            _two_modules, api_metadata_no_extras, security_config_none
        )
        assert "Contact:" not in code

    # --- Import structure ---

    def test_imports_modular_servers(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from servers.pet_server import mcp as pet_mcp" in code
        assert "from servers.store_server import mcp as store_mcp" in code

    def test_imports_fastmcp(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from fastmcp import FastMCP" in code

    # --- Authentication variants ---

    def test_no_auth_has_no_jwt_verifier(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "create_jwt_verifier" not in code
        assert "validate-tokens" not in code

    def test_bearer_auth_has_jwt_verifier(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_jwt_verifier" in code
        assert "validate-tokens" in code

    def test_auth_middleware_always_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ApiClientContextMiddleware" in code

    # --- Tool count ---

    def test_total_tool_count_matches(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        # 3 + 4 = 7
        assert "TOTAL_TOOL_COUNT = 7" in code

    # --- create_server factory ---

    def test_has_create_server_factory(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """create_server() is required by fastmcp CLI (dev/run/install)."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "async def create_server()" in code
        assert "return app" in code

    # --- FastMCP middleware ---

    def test_middleware_imports(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ErrorHandlingMiddleware" in code
        assert "DetailedTimingMiddleware" in code
        assert "LoggingMiddleware" in code

    # --- FastMCP 4 features ---

    def test_response_limiting_middleware_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ResponseLimitingMiddleware" in code

    def test_ping_middleware_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "PingMiddleware" in code

    def test_search_tools_transform_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "SearchTools" in code

    def test_code_mode_transform_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "CodeMode" in code

    def test_features_config_loading(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "_features_config" in code
        assert "fastmcp.json" in code

    def test_transforms_passed_to_fastmcp(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "transforms=_transforms" in code

    def test_opentelemetry_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "TracerProvider" in code
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" in code

    def test_dynamic_visibility_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "dynamic_visibility" in code

    def test_multi_auth_import_with_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_multi_auth_verifier" in code

    # --- FastMCP 3.1 branch-level tests ---

    def test_version_filter_transform_block(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """VersionFilter transform must appear in the generated code."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "VersionFilter" in code
        assert "version_filter" in code
        assert "include_unversioned" in code

    def test_version_filter_import_fallback(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """VersionFilter import must have an ImportError fallback."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from fastmcp.server.transforms import VersionFilter" in code
        # Verify the fallback is present
        assert "VersionFilter = None" in code

    def test_version_filter_config_keys(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """VersionFilter should read version_gte, version_lt, include_unversioned from config."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert '"version_gte"' in code
        assert '"version_lt"' in code
        assert '"include_unversioned"' in code

    def test_search_result_serializer_block(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """Generated code must support search result serializer selection."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "search_result_serializer" in code
        assert "serialize_tools_for_output_markdown" in code
        assert "serialize_tools_for_output_json" in code

    def test_bm25_search_transform_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """SearchTools should use BM25SearchTransform from fastmcp 3.1."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from fastmcp.server.transforms.search import BM25SearchTransform" in code
        assert "BM25SearchTransform(" in code

    def test_propelauth_block_in_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """PropelAuth provider should be wired into HTTP token validation."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_propelauth_provider" in code
        assert "propelauth" in code

    def test_multi_auth_provider_composition(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """MultiAuth should compose multiple providers with fallback to single JWT."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        # MultiAuth config block
        assert "_multi_auth_cfg" in code
        assert "_propelauth_cfg" in code
        # Fallback path
        assert "jwt_verifier = create_jwt_verifier()" in code
        assert "jwt_verifier = None" in code

    def test_multi_auth_provider_priority(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """PropelAuth should be checked before MultiAuth, MultiAuth before single JWT."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        propelauth_pos = code.index('_propelauth_cfg.get("enabled"')
        multi_auth_pos = code.index('_multi_auth_cfg.get("enabled"')
        fallback_pos = code.index("jwt_verifier = create_jwt_verifier()")
        assert propelauth_pos < multi_auth_pos < fallback_pos

    def test_response_limiting_config_branch(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """ResponseLimitingMiddleware must read max_size_bytes from config."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "max_size_bytes" in code
        assert "1_048_576" in code  # Default 1MB
        assert "ResponseLimitingMiddleware(max_size=" in code

    def test_ping_middleware_disabled_branch(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """PingMiddleware should check 'enabled' config key."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert '_ping_cfg.get("enabled"' in code

    def test_code_mode_import_error_fallback(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """CodeMode import must have ImportError fallback."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from fastmcp.experimental.transforms.code_mode import CodeMode" in code

    def test_no_auth_no_propelauth_block(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """Without auth, PropelAuth and MultiAuth blocks should not appear."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "create_propelauth_provider" not in code
        assert "create_multi_auth_verifier" not in code

    def test_http_validation_uvicorn_path(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """HTTP validation block should include uvicorn dispatch."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "uvicorn.Config" in code
        assert "uvicorn.Server" in code

    def test_transforms_list_building(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """Transforms list should be built incrementally."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "_transforms = []" in code
        assert "_transforms.append(BM25SearchTransform(" in code
        assert "_transforms.append(CodeMode())" in code
        assert "_transforms.append(_VF(" in code

    # --- FastMCP 3.1 new features: Rate limiting, OAuth Proxy ---

    def test_rate_limiting_middleware_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """RateLimitingMiddleware import should be present."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "RateLimitingMiddleware" in code

    def test_rate_limiting_config_block(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """Rate limiting should read max_requests_per_second, burst_capacity, global_limit."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "_rate_limit_cfg" in code
        assert "max_requests_per_second" in code
        assert "burst_capacity" in code
        assert "global_limit" in code

    def test_oauth_proxy_import_with_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """OAuth Proxy import should be present when auth is configured."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_oauth_proxy" in code

    def test_oauth_proxy_config_block(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """OAuth Proxy configuration block should read from features config."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "_oauth_proxy_cfg" in code
        assert "create_oauth_proxy(_oauth_proxy_cfg)" in code

    def test_oauth_proxy_uses_http_app_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """OAuth Proxy should use app.http_app(auth=_oauth_proxy)."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "auth=_oauth_proxy" in code

    def test_oauth_proxy_before_jwt_fallback(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        """OAuth Proxy check should come after jwt_verifier setup but before ASGI middleware."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        proxy_pos = code.index("_oauth_proxy_cfg")
        jwt_pos = code.index("jwt_verifier = create_jwt_verifier()")
        assert proxy_pos > jwt_pos

    # --- MCP Apps (--enable-apps) ---

    def test_apps_disabled_by_default(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """Without enable_apps, display tools import should not be present."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "display_tools" not in code

    def test_apps_imports_display_tools(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """enable_apps=True should import display_tools_mcp from apps package."""
        code = generate_main_composition_server(
            _two_modules, api_metadata, security_config_none, enable_apps=True
        )
        assert "from apps.display_tools import mcp as display_tools_mcp" in code

    def test_apps_mounts_display_namespace(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """enable_apps=True should mount display tools under 'display' namespace."""
        code = generate_main_composition_server(
            _two_modules, api_metadata, security_config_none, enable_apps=True
        )
        assert 'mount(display_tools_mcp, namespace="display")' in code

    def test_apps_generative_ui_conditional(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """GenerativeUI import should be conditional on fastmcp.json config."""
        code = generate_main_composition_server(
            _two_modules, api_metadata, security_config_none, enable_apps=True
        )
        assert "GenerativeUI" in code
        assert "_generative_ui_enabled" in code
        assert "add_provider" in code

    def test_apps_generative_ui_import_fallback(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """GenerativeUI import should have ImportError fallback."""
        code = generate_main_composition_server(
            _two_modules, api_metadata, security_config_none, enable_apps=True
        )
        assert "ImportError" in code
        assert "_generative_ui_provider = None" in code


# ---------------------------------------------------------------------------
# write_apps_package
# ---------------------------------------------------------------------------


class TestWriteAppsPackage:
    """Test that write_apps_package creates the expected file structure."""

    def test_creates_apps_directory(self, tmp_path: Path) -> None:
        from mcp_generator.writers import write_apps_package

        write_apps_package(tmp_path)
        assert (tmp_path / "apps").is_dir()

    def test_creates_display_tools(self, tmp_path: Path) -> None:
        from mcp_generator.writers import write_apps_package

        write_apps_package(tmp_path)
        dt = tmp_path / "apps" / "display_tools.py"
        assert dt.exists()
        content = dt.read_text(encoding="utf-8")
        assert "show_table" in content
        assert "show_detail" in content
        assert "show_chart" in content
        assert "show_metrics" in content
        assert "show_timeline" in content
        assert "show_progress" in content

    def test_creates_init_py(self, tmp_path: Path) -> None:
        from mcp_generator.writers import write_apps_package

        write_apps_package(tmp_path)
        init = tmp_path / "apps" / "__init__.py"
        assert init.exists()
        content = init.read_text(encoding="utf-8")
        assert "display_tools_mcp" in content

    def test_idempotent(self, tmp_path: Path) -> None:
        """Running write_apps_package twice should not error."""
        from mcp_generator.writers import write_apps_package

        write_apps_package(tmp_path)
        write_apps_package(tmp_path)
        assert (tmp_path / "apps" / "display_tools.py").exists()
