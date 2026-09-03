"""Tests for the FastMCP target-version matrix and the code it drives.

The behavioural tests here are regression guards for the FastMCP 4 migration:
every construct asserted absent from a target=4 render is one that was verified
to break against the real ``fastmcp==4.0.2`` package.
"""

import pytest

from mcp_generator.config import CLIENT_REQUIRED_MCP_METHODS
from mcp_generator.fastmcp_target import SUPPORTED_TARGETS, resolve_target
from mcp_generator.models import ApiMetadata, SecurityConfig
from mcp_generator.templates.authentication import generate_authentication_middleware
from mcp_generator.templates.oauth_provider import generate_oauth_provider


class TestTargetResolution:
    def test_defaults_to_configured_target(self):
        assert resolve_target().major == 4

    def test_supports_three_and_four(self):
        assert SUPPORTED_TARGETS == (3, 4)

    def test_unsupported_major_raises(self):
        with pytest.raises(ValueError, match="Unsupported FastMCP target"):
            resolve_target(99)


class TestDependencyPins:
    def test_v3_pin_excludes_v4(self):
        assert resolve_target(3).dependency_pin() == "fastmcp>=3.2.4,<4.0.0"

    def test_v4_pin_is_a_stable_range(self):
        # 4.0.0 went GA 2026-08-31; 4.0.2 is the floor we verified against.
        target = resolve_target(4)
        assert target.dependency_pin() == "fastmcp>=4.0.2,<5.0.0"
        assert not target.is_prerelease

    def test_apps_extra_applies_to_both(self):
        assert resolve_target(3).dependency_pin(enable_apps=True).startswith("fastmcp[apps]")
        assert resolve_target(4).dependency_pin(enable_apps=True).startswith("fastmcp[apps]")

    def test_v4_floors_pydantic_at_sdk_v2_requirement(self):
        # SDK v2 fails resolution outright below 2.12 rather than upgrading.
        assert resolve_target(4).pydantic_pin == "pydantic>=2.12,<3.0.0"

    def test_v3_pydantic_floor_matches_the_generator_requirement(self):
        # The generated client is produced by this generator, so the emitted
        # floor tracks the generator's own pydantic requirement.
        assert resolve_target(3).pydantic_pin == "pydantic>=2.10.3,<3.0.0"


class TestErrorConstruction:
    def test_v3_wraps_error_data(self):
        target = resolve_target(3)
        assert (
            target.render_mcp_error("-32001", '"boom"')
            == 'McpError(ErrorData(code=-32001, message="boom"))'
        )
        assert "from mcp.types import ErrorData" in target.error_imports

    def test_v4_uses_keyword_form(self):
        # The wrapped form raises TypeError against the SDK v2 class.
        target = resolve_target(4)
        assert (
            target.render_mcp_error("-32001", '"boom"') == 'McpError(code=-32001, message="boom")'
        )
        assert "ErrorData" not in target.error_imports

    def test_v4_imports_mcp_error_from_fastmcp(self):
        # `mcp.McpError` was renamed MCPError in SDK v2 and no longer resolves.
        assert resolve_target(4).error_imports == "from fastmcp.exceptions import McpError"


class TestServerCapabilities:
    def test_server_sampling_removed_in_v4(self):
        assert resolve_target(3).supports_server_sampling
        assert not resolve_target(4).supports_server_sampling

    def test_elicitation_unreachable_by_default_client_in_v4(self):
        assert resolve_target(3).elicitation_reaches_default_client
        assert not resolve_target(4).elicitation_reaches_default_client


@pytest.fixture
def metadata() -> ApiMetadata:
    return ApiMetadata(title="Target API", description="d", version="1.0.0")


@pytest.fixture
def bearer_config() -> SecurityConfig:
    return SecurityConfig(
        schemes={"bearerAuth": {"type": "http", "scheme": "bearer"}},
        global_security=[{"bearerAuth": []}],
        default_scopes=["read"],
    )


class TestGeneratedAuthMiddleware:
    """The auth middleware is where every verified v4 import break lived."""

    def test_v3_render_uses_mcp_package_import(self, metadata, bearer_config):
        code = generate_authentication_middleware(metadata, bearer_config, target=resolve_target(3))
        assert "from mcp import McpError" in code
        assert "from mcp.types import ErrorData" in code

    def test_v4_render_avoids_renamed_mcp_symbol(self, metadata, bearer_config):
        code = generate_authentication_middleware(metadata, bearer_config, target=resolve_target(4))
        assert "from mcp import McpError" not in code
        assert "from fastmcp.exceptions import McpError" in code

    def test_v4_render_uses_keyword_error_construction(self, metadata, bearer_config):
        code = generate_authentication_middleware(metadata, bearer_config, target=resolve_target(4))
        assert "McpError(ErrorData(" not in code
        assert "McpError(code=" in code

    @pytest.mark.parametrize("major", [3, 4])
    def test_error_message_interpolates_the_exception(self, metadata, bearer_config, major):
        # A doubled brace survives substitution verbatim and would emit the
        # literal text "{exc}" instead of the exception at runtime.
        code = generate_authentication_middleware(
            metadata, bearer_config, target=resolve_target(major)
        )
        assert 'f"Authentication failed: {exc}"' in code
        assert "{{exc}}" not in code


class TestGeneratedOAuthProvider:
    def test_v3_render_uses_httpx(self, metadata, bearer_config):
        code = generate_oauth_provider(metadata, bearer_config, target=resolve_target(3))
        assert "import httpx\n" in code

    def test_v4_render_uses_httpx2(self, metadata, bearer_config):
        # FastMCP 4 replaced httpx wholesale; httpx is not a dependency of it.
        code = generate_oauth_provider(metadata, bearer_config, target=resolve_target(4))
        assert "import httpx2" in code
        assert "import httpx\n" not in code


class TestClientRequiredMethodGuard:
    """Dispatch moved into the SDK middleware layer, so on_request sees every
    inbound message. Only tool calls and resource reads consume the API client."""

    @pytest.mark.parametrize("major", [3, 4])
    def test_guard_skips_methods_that_cannot_use_the_client(self, metadata, bearer_config, major):
        code = generate_authentication_middleware(
            metadata, bearer_config, target=resolve_target(major)
        )
        assert "CLIENT_REQUIRED_METHODS" in code
        assert "not in CLIENT_REQUIRED_METHODS" in code
        for method in CLIENT_REQUIRED_MCP_METHODS:
            assert f'"{method}"' in code or f"'{method}'" in code

    def test_emitted_guard_set_is_deterministic(self, metadata, bearer_config):
        # Set repr order varies per process; generated output must not.
        code = generate_authentication_middleware(metadata, bearer_config, target=resolve_target(4))
        expected = "{" + ", ".join(repr(m) for m in sorted(CLIENT_REQUIRED_MCP_METHODS)) + "}"
        assert f"CLIENT_REQUIRED_METHODS = {expected}" in code

    def test_guard_covers_both_state_reading_handlers(self):
        # Generated tools and generated resources both read openapi_client.
        assert set(CLIENT_REQUIRED_MCP_METHODS) == {"tools/call", "resources/read"}
