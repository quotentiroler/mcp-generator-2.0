"""Assembles the main server that mounts every module."""

from ..fastmcp_target import FastMCPTarget, resolve_target
from ..models import ApiMetadata, ModuleSpec, SecurityConfig
from .runtime_template import _RUNTIME_TAIL


def generate_main_composition_server(
    modules: dict[str, ModuleSpec],
    api_metadata: ApiMetadata,
    security_config: SecurityConfig,
    composition_strategy: str = "mount",
    resource_prefix_format: str = "path",
    enable_apps: bool = False,
    display_tags: list[str] | None = None,
    target: FastMCPTarget | None = None,
) -> str:
    """Generate main server that composes all modular servers.

    Emits code for the FastMCP major named by ``target`` (see fastmcp_target.py).

    Key FastMCP 3.x changes vs 2.x:
      - ``mount(prefix=...)`` → ``mount(namespace=...)``
      - ``import_server(...)`` is deprecated → use ``mount(...)``
      - ``ctx.get_state()`` / ``ctx.set_state()`` are now **async**
      - ``resource_prefix_format`` constructor kwarg removed
      - ``create_streamable_http_app(...)`` → ``mcp.http_app(...)``
      - ``InMemoryEventStore`` → ``EventStore`` from ``fastmcp.server.event_store``

    FastMCP 4 features (generated when enabled in fastmcp.json):
      - ``BM25SearchTransform`` for BM25 tool discovery
      - ``CodeMode`` experimental transform for meta-tool execution
      - ``VersionFilter`` transform with ``include_unversioned`` support
      - ``ResponseLimitingMiddleware`` for safe response truncation
      - ``RateLimitingMiddleware`` for token-bucket abuse prevention
      - ``PingMiddleware`` for HTTP keepalive
      - ``MultiAuth`` for composing multiple token verifiers
      - ``PropelAuth`` as built-in auth provider option
      - ``KeycloakAuthProvider`` for Keycloak enterprise auth
      - ``OAuthProxy`` for bridging non-DCR IdPs (Auth0, Okta, Azure AD)
      - ``search_result_serializer`` hook for custom search output
      - Component versioning via ``version=`` on ``@mcp.tool()``
      - Tool tags via ``tags=`` on ``@mcp.tool()``
      - Tool timeouts via ``timeout=`` on ``@mcp.tool()``
      - ``validate_output=False`` for OpenAPI backends
      - Dynamic per-session component visibility
      - OpenTelemetry tracing with MCP semantic conventions
      - ``ctx.report_progress()`` for tool progress reporting
      - SSRF-safe fetch for JWKS/introspection endpoints

    Target-dependent (see fastmcp_target.py):
      - ``ctx.elicit()`` collects missing parameters on 3.x; on 4.x the tool
        reports them back, since elicitation cannot reach a default client
      - ``ctx.sample()`` aids error recovery on 3.x; removed from the server
        API in 4.x

    Args:
        modules: Dictionary of module specifications
        api_metadata: API metadata from OpenAPI spec
        security_config: Security configuration
        composition_strategy: "mount" (default, recommended for v3)
        resource_prefix_format: Ignored in v3 (kept for config compat)
        target: FastMCP major version matrix to generate against
    """
    target = target or resolve_target()
    _missing_param_note = (
        "ctx.elicit() asks the client for them"
        if target.elicitation_reaches_default_client
        else "reported back to the caller (elicitation is unavailable on 2026-07-28)"
    )
    module_names = sorted(modules.keys())
    total_tool_count = sum(spec.tool_count for spec in modules.values())

    # Sanitize metadata for safe embedding in generated Python string literals
    from dataclasses import replace as _dc_replace

    api_metadata = _dc_replace(
        api_metadata,
        title=api_metadata.title.replace("\\", "\\\\").replace('"', '\\"'),
        description=api_metadata.description.replace("\\", "\\\\").replace('"""', '\\"\\"\\"'),
    )

    # Build import statements using the actual generated filename from ModuleSpec
    imports = "\n".join(
        [
            f"from servers.{modules[name].filename.replace('.py', '')} import mcp as {name}_mcp"
            for name in module_names
        ]
    )

    # In FastMCP 3.x mount() is synchronous and the recommended approach.
    # import_server() is deprecated → always use mount(namespace=...).
    compositions = "\n    ".join(
        [f'app.mount({name}_mcp, namespace="{name}")' for name in module_names]
    )

    # --- MCP Apps: display tools and GenerativeUI ---
    apps_import = ""
    apps_composition = ""
    if enable_apps:
        apps_import = """
# MCP Apps: curated display tools (tables, charts, forms, detail views)
from apps.display_tools import mcp as display_tools_mcp
"""
        apps_composition = '    app.mount(display_tools_mcp, namespace="display")'
        # Check if GenerativeUI is enabled in fastmcp.json config
        apps_import += """
# MCP Apps: GenerativeUI (LLM-generated UIs at runtime) — conditional on fastmcp.json
_apps_cfg = _features_config.get("apps", {})
_generative_ui_enabled = _apps_cfg.get("generative_ui", False)
if _generative_ui_enabled:
    try:
        from fastmcp.apps.generative import GenerativeUI
        _generative_ui_provider = GenerativeUI()
    except ImportError:
        _generative_ui_provider = None
        import logging as _logging
        _logging.getLogger(__name__).warning("GenerativeUI requires fastmcp[apps]>=3.2.4")
else:
    _generative_ui_provider = None
"""
        apps_composition += """
    if _generative_ui_provider is not None:
        app.add_provider(_generative_ui_provider)
        try:
            print("  🎨 GenerativeUI provider enabled (LLM-generated UIs)")
        except UnicodeEncodeError:
            print("  GenerativeUI provider enabled")\
"""
        # Mount API-specific display modules (Phase 2)
        if display_tags:
            apps_import += "\n# API-specific display tools (generated from response schemas)\n"
            for tag in sorted(display_tags):
                var = f"{tag}_display_mcp"
                apps_import += f"from apps.{tag}_display import mcp as {var}\n"
                apps_composition += f'\n    app.mount({var}, namespace="{tag}_ui")'
    # Build comprehensive header
    header_lines = [
        '"""',
        f"{api_metadata.title} MCP Server - Main Composition.",
        "",
        f"{api_metadata.description}",
        f"Version: {api_metadata.version}",
    ]

    if api_metadata.contact and api_metadata.contact.get("email"):
        header_lines.append(f"Contact: {api_metadata.contact['email']}")
    if api_metadata.license and api_metadata.license.get("name"):
        header_lines.append(f"License: {api_metadata.license['name']}")
    if api_metadata.external_docs and api_metadata.external_docs.get("url"):
        header_lines.append(f"Documentation: {api_metadata.external_docs['url']}")

    header_lines.extend(
        [
            "",
            "This server composes all modular API servers into a unified MCP interface.",
            "Composition: mount() with namespace isolation",
            "",
            "FastMCP Features:",
            "  - Tool tags: Auto-tagged from OpenAPI tags for filtering",
            "  - Tool timeouts: 30s default (configurable in fastmcp.json)",
            "  - SearchTools: BM25 tool discovery (enable in fastmcp.json)",
            "  - CodeMode: Experimental meta-tool transform (enable in fastmcp.json)",
            "  - ResponseLimiting: UTF-8-safe response truncation",
            "  - RateLimiting: Token-bucket abuse prevention (enable in fastmcp.json)",
            "  - PingMiddleware: HTTP keepalive",
            "  - OAuthProxy: Bridge non-DCR IdPs to MCP auth (enable in fastmcp.json)",
            "  - Component versioning: Deprecated endpoints marked with version",
            "  - Progress reporting: ctx.report_progress() in every tool",
            f"  - Missing parameters: {_missing_param_note}",
            *(
                []
                if not target.supports_server_sampling
                else ["  - Sampling: ctx.sample() for LLM-assisted error recovery"]
            ),
            "  - SSRF protection: JWKS/introspection endpoint validation",
            "  - OpenTelemetry: Tracing support (enable in fastmcp.json)",
            "",
            "Auto-generated by mcp_generator.",
            "DO NOT EDIT MANUALLY - regenerate using: python -m mcp_generator",
            "Configuration: fastmcp.json",
            '"""',
        ]
    )

    header_doc = "\n".join(header_lines)

    # --- Authentication imports (always need middleware for openapi_client) ---
    auth_imports = """
# Import API client middleware (required even without authentication)
from middleware.authentication import ApiClientContextMiddleware
"""
    auth_middleware_setup = """
    app.add_middleware(ApiClientContextMiddleware(
        transport_mode=args.transport,
        validate_tokens=False  # Token validation is done at ASGI layer for HTTP
    ))"""
    auth_argparse = ""
    auth_validation = ""

    if security_config.has_authentication():
        auth_imports += """from middleware.oauth_provider import create_jwt_verifier, build_authentication_stack, RequireScopesMiddleware, create_multi_auth_verifier, create_propelauth_provider, create_keycloak_provider, create_oauth_proxy
"""
        auth_argparse = """
    parser.add_argument(
        "--validate-tokens",
        action="store_true",
        default=default_validate_tokens,
        help=f"Enable JWT token validation for HTTP transport (default: {{default_validate_tokens}}, configurable in fastmcp.json)"
    )
"""
        auth_validation = """
    # Validate that --validate-tokens only works with HTTP transport
    if args.validate_tokens and args.transport != "http":
        logger.warning("⚠️  --validate-tokens is only applicable for HTTP transport, ignoring for STDIO mode")
        args.validate_tokens = False
"""

    # --- HTTP token-validation block (only when auth is configured) ---
    if security_config.has_authentication():
        http_token_validation_block = """
        # For HTTP transport with token validation, use ASGI middleware
        if hasattr(args, 'validate_tokens') and args.validate_tokens:
            logger.info("  🔧 ASGI Middleware: Authentication (JWT validation) at HTTP layer")
            logger.info("  🔑 JWT validation: Enabled via Starlette auth backend + scope guard")

            # Check auth provider priority: PropelAuth > Keycloak > MultiAuth > JWT
            _multi_auth_cfg = _features_config.get("multi_auth", {})
            _propelauth_cfg = _features_config.get("propelauth", {})
            _keycloak_cfg = _features_config.get("keycloak", {})
            jwt_verifier = None

            if _propelauth_cfg.get("enabled", False):
                # Use PropelAuth as the authentication provider
                propelauth_provider = create_propelauth_provider(_propelauth_cfg)
                if propelauth_provider:
                    logger.info("  🔐 PropelAuth provider configured")
                    # PropelAuth acts as both auth provider and verifier
                    jwt_verifier = propelauth_provider

            if jwt_verifier is None and _keycloak_cfg.get("enabled", False):
                # Use Keycloak native DCR provider
                keycloak_provider = create_keycloak_provider(_keycloak_cfg)
                if keycloak_provider:
                    logger.info("  🔐 Keycloak provider configured")
                    jwt_verifier = keycloak_provider

            if jwt_verifier is None and _multi_auth_cfg.get("enabled", False):
                # MultiAuth: compose multiple token verifiers
                multi_auth = create_multi_auth_verifier(_multi_auth_cfg.get("providers", []))
                if multi_auth:
                    jwt_verifier = multi_auth
                    logger.info("  🔐 MultiAuth verifier configured with %d providers", len(_multi_auth_cfg.get("providers", [])) + 1)

            if jwt_verifier is None:
                # Fallback: single JWT verifier
                jwt_verifier = create_jwt_verifier()

            # Check if OAuthProxy is configured (bridges non-DCR IdPs)
            _oauth_proxy_cfg = _features_config.get("oauth_proxy", {})
            _oauth_proxy = None
            if _oauth_proxy_cfg.get("enabled", False):
                _oauth_proxy = create_oauth_proxy(_oauth_proxy_cfg)
                if _oauth_proxy:
                    logger.info("  🔀 OAuthProxy configured - bridging upstream IdP to MCP DCR")

            if _oauth_proxy:
                # Use OAuthProxy as the auth provider for the HTTP app
                from fastmcp.server.event_store import EventStore

                event_store = EventStore()
                http_app = app.http_app(
                    path="/mcp",
                    event_store=event_store,
                    auth=_oauth_proxy,
                )

                import uvicorn, anyio
                logger.info("  ✅ OAuthProxy configured - enterprise IdP bridging active")
                config = uvicorn.Config(http_app, host=args.host, port=args.port, log_level="info")
                uvicorn_server = uvicorn.Server(config)
                anyio.run(uvicorn_server.serve)
            elif jwt_verifier:
                asgi_middleware = build_authentication_stack(jwt_verifier, require_auth=True)

                from fastmcp.server.event_store import EventStore

                event_store = EventStore()
                http_app = app.http_app(
                    path="/mcp",
                    event_store=event_store,
                    middleware=asgi_middleware if asgi_middleware else None,
                )

                import uvicorn, anyio
                logger.info("  ✅ ASGI middleware configured with token enforcement")
                config = uvicorn.Config(http_app, host=args.host, port=args.port, log_level="info")
                uvicorn_server = uvicorn.Server(config)
                anyio.run(uvicorn_server.serve)
            else:
                logger.warning("  ⚠️ JWT verifier initialization failed - falling back to backend validation")
                app.run(transport="http", host=args.host, port=args.port)
        else:
            logger.info("  🔧 FastMCP Middleware: Error handling → Auth (backend validation) → Timing → Logging")
            app.run(transport="http", host=args.host, port=args.port)"""
    else:
        http_token_validation_block = """
        logger.info("  🔧 FastMCP Middleware: Error handling → Auth (backend validation) → Timing → Logging")
        app.run(transport="http", host=args.host, port=args.port)"""

    # --- Build the generated code ---
    code = f'''{header_doc}

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

# FastMCP middleware imports
try:
    # Lives in its own module since FastMCP 3.2; it was under rate_limiting in 3.1.
    from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
except ImportError:  # pragma: no cover - FastMCP 3.1 layout
    try:
        from fastmcp.server.middleware.rate_limiting import ResponseLimitingMiddleware
    except ImportError:
        ResponseLimitingMiddleware = None

try:
    from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
except ImportError:
    RateLimitingMiddleware = None  # FastMCP <3.1

try:
    from fastmcp.server.middleware.ping import PingMiddleware
except ImportError:
    PingMiddleware = None  # FastMCP <3.0

# VersionFilter import
try:
    from fastmcp.server.transforms import VersionFilter
except ImportError:
    VersionFilter = None  # FastMCP <3.1

# Add the src folder and generated folder to the Python path
src_path = Path(__file__).parent
generated_path = src_path.parent / "generated_openapi"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

# Import all modular servers
{imports}{auth_imports}
logger = logging.getLogger(__name__)

# --- Load feature configuration from fastmcp.json ---
_features_config = {{}}
_fastmcp_json = Path(__file__).parent / "fastmcp.json"
if _fastmcp_json.exists():
    try:
        import json as _json
        with open(_fastmcp_json, "r", encoding="utf-8") as _f:
            _fc = _json.load(_f)
            _features_config = _fc.get("features", {{}})
    except Exception:
        pass
{apps_import}
# --- Build transforms list ---
_transforms = []

# SearchTools: BM25 text search over tool catalog for large servers
_search_tools_cfg = _features_config.get("search_tools", {{}})
if _search_tools_cfg.get("enabled", False):
    try:
        from fastmcp.server.transforms.search import BM25SearchTransform
        _search_kwargs = {{}}
        # Custom search result serializer
        _serializer_cfg = _search_tools_cfg.get("serializer")
        if _serializer_cfg == "markdown":
            from fastmcp.server.transforms.search import serialize_tools_for_output_markdown
            _search_kwargs["search_result_serializer"] = serialize_tools_for_output_markdown
        elif _serializer_cfg == "json":
            from fastmcp.server.transforms.search import serialize_tools_for_output_json
            _search_kwargs["search_result_serializer"] = serialize_tools_for_output_json
        _transforms.append(BM25SearchTransform(**_search_kwargs))
        logger.info("  🔍 BM25SearchTransform enabled (BM25 tool discovery)")
    except ImportError:
        logger.warning("  ⚠️ BM25SearchTransform not available")

# VersionFilter: Filter components by version
_version_filter_cfg = _features_config.get("version_filter", {{}})
if _version_filter_cfg.get("enabled", False):
    try:
        from fastmcp.server.transforms import VersionFilter as _VF
        _vf_kwargs = {{}}
        if "version_gte" in _version_filter_cfg:
            _vf_kwargs["version_gte"] = _version_filter_cfg["version_gte"]
        if "version_lt" in _version_filter_cfg:
            _vf_kwargs["version_lt"] = _version_filter_cfg["version_lt"]
        _vf_kwargs["include_unversioned"] = _version_filter_cfg.get("include_unversioned", True)
        _transforms.append(_VF(**_vf_kwargs))
        logger.info("  📦 VersionFilter transform enabled (include_unversioned=%s)", _vf_kwargs["include_unversioned"])
    except ImportError:
        logger.warning("  ⚠️ VersionFilter not available")

# CodeMode: Experimental meta-tool transform (search → inspect → execute)
_code_mode_cfg = _features_config.get("code_mode", {{}})
if _code_mode_cfg.get("enabled", False):
    try:
        from fastmcp.experimental.transforms.code_mode import CodeMode
        _transforms.append(CodeMode())
        logger.info("  🧪 CodeMode transform enabled (experimental)")
    except ImportError:
        logger.warning("  ⚠️ CodeMode not available")

# Create main FastMCP server (using 'app' for fastmcp auto-detection)
app = FastMCP(
    "{api_metadata.title}",
    transforms=_transforms if _transforms else None,
)


def _compose_mcp_servers():
    """Compose all modular servers into the main server.

    Uses mount(namespace=...) for composition .
    Changes to mounted subservers are immediately reflected.
    """
    try:
        print("🔗 Composing modular servers...")
    except UnicodeEncodeError:
        print("Composing modular servers...")
    {compositions}
{apps_composition}
    try:
        print(f"✅ Server composition complete - {total_tool_count} MCP tools registered")
    except UnicodeEncodeError:
        print(f"[OK] Server composition complete - {total_tool_count} MCP tools registered")


async def create_server() -> FastMCP:
    """
    Factory function for fastmcp CLI (run, dev, install, inspect).

    Composes all modular servers and returns the configured main server.
    This is the REQUIRED entrypoint for fastmcp commands.

    Usage:
        fastmcp dev server.py:create_server
        fastmcp run server.py:create_server
        fastmcp install claude-desktop server.py:create_server

    Returns:
        FastMCP: The fully composed and configured server instance
    """
    _compose_mcp_servers()
    return app


# API Metadata (extracted during generation)
API_TITLE = "{api_metadata.title}"
API_DESCRIPTION = """{api_metadata.description}"""
API_VERSION = "{api_metadata.version}"
TOTAL_TOOL_COUNT = {total_tool_count}

def main():
    """Run the FastMCP backend tools server."""
    import argparse
    import json
    from pathlib import Path

    # Try to load fastmcp.json for default configuration
    fastmcp_config = {{}}
    fastmcp_path = Path(__file__).parent / "fastmcp.json"
    if fastmcp_path.exists():
        try:
            with open(fastmcp_path, "r", encoding="utf-8") as f:
                fastmcp_config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load fastmcp.json: {{e}}")

    # Get default validate_tokens from config (handle both bool and string values)
    _raw_validate = fastmcp_config.get("middleware", {{}}).get("config", {{}}).get("authentication", {{}}).get("validate_tokens", False)
    default_validate_tokens = _raw_validate if isinstance(_raw_validate, bool) else str(_raw_validate).lower() not in ("false", "0", "no", "")

    # Build comprehensive description
    description_parts = [f"{{API_TITLE}} - FastMCP MCP Server"]
    if API_DESCRIPTION:
        description_parts.append(API_DESCRIPTION)
    if API_VERSION:
        description_parts.append(f"Version: {{API_VERSION}}")

    parser = argparse.ArgumentParser(
        description="\\n".join(description_parts),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP transport (default: 8000)"
    )
{auth_argparse}
    args = parser.parse_args()
{auth_validation}
    # Add FastMCP middleware stack (order matters!)
'''
    code += _RUNTIME_TAIL.format(
        api_metadata=api_metadata,
        auth_middleware_setup=auth_middleware_setup,
        http_token_validation_block=http_token_validation_block,
        module_count=len(module_names),
    )

    return code
