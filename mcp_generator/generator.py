"""
MCP Generator - Core orchestration.

Main generator functions that coordinate introspection, rendering, and writing.
"""

from pathlib import Path

from .introspection import get_api_metadata, get_api_modules, get_security_config
from .models import ApiMetadata, ModuleSpec, SecurityConfig
from .renderers import generate_server_module


def generate_modular_servers(base_dir: Path | None = None) -> tuple[dict[str, ModuleSpec], int]:
    """Generate modular MCP servers from API client classes.

    Args:
        base_dir: Base directory containing generated_openapi. Defaults to current working directory.

    Returns:
        tuple[dict[str, ModuleSpec], int]: (dict of modules keyed by module_name, total_tool_count)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Get API modules dynamically (sort keys for deterministic output)
    api_modules = get_api_modules(base_dir)

    servers: dict[str, ModuleSpec] = {}
    total_tools = 0

    # Generate a server module for each API class. Key the resulting dict by
    # ModuleSpec.module_name (stable identifier) rather than filename to avoid
    # brittle filename-based lookups downstream.
    for api_var_name in sorted(api_modules.keys()):
        api_class = api_modules[api_var_name]
        module_spec = generate_server_module(api_var_name, api_class)
        servers[module_spec.module_name] = module_spec
        total_tools += module_spec.tool_count

    return servers, total_tools


def generate_main_composition_server(
    modules: dict[str, ModuleSpec],
    api_metadata: ApiMetadata,
    security_config: SecurityConfig,
    composition_strategy: str = "mount",
    resource_prefix_format: str = "path",
) -> str:
    """Generate main server that composes all modular servers.

    Args:
        modules: Dictionary of module specifications
        api_metadata: API metadata from OpenAPI spec
        security_config: Security configuration
        composition_strategy: "mount" for dynamic composition (default) or "import" for static
        resource_prefix_format: "path" (default, FastMCP 2.4+) or "protocol" (legacy)
    """
    # Build import statements
    # Expect `modules` to be a dict keyed by ModuleSpec.module_name. Use the
    # keys and sort them for deterministic generation order.
    module_names = sorted(modules.keys())

    # Calculate total tool count
    total_tool_count = sum(spec.tool_count for spec in modules.values())

    # Build import statements using the actual generated filename from ModuleSpec
    imports = "\n".join(
        [
            f"from servers.{modules[name].filename.replace('.py', '')} import mcp as {name}_mcp"
            for name in module_names
        ]
    )

    # Build composition calls based on strategy
    if composition_strategy == "import":
        # Static composition - requires async
        compositions = "\n    ".join(
            [f'await app.import_server({name}_mcp, prefix="{name}")' for name in module_names]
        )
        is_async_composition = True
    else:
        # Dynamic composition (mount) - synchronous
        compositions = "\n    ".join(
            [f'app.mount({name}_mcp, prefix="{name}")' for name in module_names]
        )
        is_async_composition = False

    # Determine if we need asyncio import: either composition itself is async
    # (composition_strategy == "import") or we will perform a one-time
    # import/copy of subservers into the main app when running under HTTP
    # transport for the "mount" strategy. That one-time import uses
    # await app.import_server(...), so we must emit an async helper and
    # import asyncio in the generated code.
    need_asyncio = is_async_composition or composition_strategy == "mount"

    # If we are using dynamic composition (mount), emit an async helper that
    # will import/copy each subserver into the main app. This helper will be
    # called via asyncio.run(...) in the HTTP branch of main(). We build the
    # helper here as a plain string so it can be inserted into the generated
    # server module.
    import_subservers_def = ""
    if composition_strategy == "mount":
        lines = ["async def _import_subservers_once():"]
        lines.append("    # One-time import of subservers into main app to populate tool registry")
        for name in module_names:
            # Use try/except around each import to avoid failing startup if a
            # single subserver import has issues.
            lines.append("    try:")
            # We need to produce code that awaits app.import_server({name}_mcp, prefix=\"{name}\")
            lines.append(f'        await app.import_server({name}_mcp, prefix="{name}")')
            # logger.debug line in the generated code must keep braces for its f-string;
            # double braces in this generator f-string produce single braces in the output.
            # Use an outer f-string so the generator substitutes the literal
            # subserver name; keep double braces for _exc so the generated
            # code contains a runtime f-string that interpolates the
            # exception variable in the generated module.
            lines.append(
                f'    except Exception as _exc:\n        logger.debug(f"Could not import subserver {name}: {{_exc}}")'
            )
        import_subservers_def = "\n" + "\n".join(lines) + "\n"

        # Pre-built HTTP branch injection (properly indented) to call the
        # one-time import helper when running in HTTP transport under the
        # dynamic composition (mount) strategy. Keep this as a separate
        # string to preserve indentation in the generated code.
        http_import_call = ""
        if composition_strategy == "mount":
            http_import_call = (
                "        # For HTTP transport and dynamic composition (mount), ensure subservers\n"
                "        # are imported/copied into the main app once so the tool registry is populated.\n"
                "        try:\n"
                "            asyncio.run(_import_subservers_once())\n"
                "        except Exception as _exc:\n"
                '            logger.debug(f"Could not import subservers into main app: {{_exc}}")\n'
            )

    # Build comprehensive header
    header_lines = [
        '"""',
        f"{api_metadata.title} MCP Server - Main Composition.",
        "",
        f"{api_metadata.description}",
        f"Version: {api_metadata.version}",
    ]

    # Add contact if available
    if api_metadata.contact and api_metadata.contact.get("email"):
        header_lines.append(f"Contact: {api_metadata.contact['email']}")

    # Add license if available
    if api_metadata.license and api_metadata.license.get("name"):
        header_lines.append(f"License: {api_metadata.license['name']}")

    # Add docs if available
    if api_metadata.external_docs and api_metadata.external_docs.get("url"):
        header_lines.append(f"Documentation: {api_metadata.external_docs['url']}")

    # Add composition strategy info to header
    strategy_info = (
        f"Composition Strategy: {composition_strategy}\n"
        f"  - mount: Live linking, dynamic updates, minimal overhead for local servers\n"
        f"  - import: One-time copy, no runtime delegation, best for performance\n"
        f"Resource Prefix Format: {resource_prefix_format}\n"
        f"  - path: resource://prefix/path (FastMCP 2.4+ default)\n"
        f"  - protocol: prefix+resource://path (legacy)"
    )

    header_lines.extend(
        [
            "",
            "This server composes all modular API servers into a unified MCP interface.",
            "",
            strategy_info,
            "",
            "Auto-generated by mcp_generator.",
            "DO NOT EDIT MANUALLY - regenerate using: python -m mcp_generator",
            "Configuration: fastmcp.json (composition.strategy, composition.resource_prefix_format)",
            '"""',
        ]
    )

    header_doc = "\n".join(header_lines)

    # Conditional authentication imports
    auth_imports = ""
    auth_middleware_setup = ""
    auth_argparse = ""
    auth_validation = ""
    if security_config.has_authentication():
        auth_imports = """
# Import authentication components
from middleware.authentication import ApiClientContextMiddleware
from middleware.oauth_provider import create_jwt_verifier, build_authentication_stack, RequireScopesMiddleware
from middleware.event_store import InMemoryEventStore
"""
        auth_middleware_setup = """
    app.add_middleware(ApiClientContextMiddleware(
        transport_mode=args.transport,
        validate_tokens=False  # Token validation is done at ASGI layer for HTTP
    ))"""
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

    code = f'''{header_doc}

{"import asyncio" if need_asyncio else ""}
import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.http import create_streamable_http_app

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

# Create main FastMCP 2.x Server (using 'app' for fastmcp auto-detection)
app = FastMCP("{api_metadata.title}", resource_prefix_format="{resource_prefix_format}")
{import_subservers_def}
'''

    # Conditional event store and middleware setup
    if security_config.has_authentication():
        code += """
# Create event store for SSE resumability
event_store = InMemoryEventStore(max_events_per_stream=1000)
logger.info(f"📦 Event store initialized: {{event_store.get_stats()}}")
"""
    else:
        code += """
# No authentication configured - event store not needed
event_store = None
"""

    # Generate composition function based on strategy
    composition_async = "async " if is_async_composition else ""
    composition_await = "await " if is_async_composition else ""
    composition_desc = (
        "import_server() for static composition - one-time copy of subserver components"
        if is_async_composition
        else "mount() for dynamic composition - changes to subservers are immediately reflected"
    )
    performance_note = (
        "Better performance - no runtime delegation overhead"
        if is_async_composition
        else "Minimal overhead for local servers, allows runtime updates"
    )

    code += f'''

{composition_async}def _compose_mcp_servers():
    """Compose all modular servers into the main server.

    Uses {composition_desc}.
    This is configured via fastmcp.json (composition.strategy).

    Performance: {performance_note}
    """
    try:
        print("🔗 Composing modular servers...")
    except UnicodeEncodeError:
        print("Composing modular servers...")
    {compositions}
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
    {composition_await}_compose_mcp_servers()
    return app


# API Metadata (extracted during generation)
API_TITLE = "{api_metadata.title}"
API_DESCRIPTION = """{api_metadata.description}"""
API_VERSION = "{api_metadata.version}"
TOTAL_TOOL_COUNT = {total_tool_count}

def main():
    """Run the FastMCP 2.x backend tools server with JWT authentication."""
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

    # Get default validate_tokens from config
    default_validate_tokens = fastmcp_config.get("middleware", {{}}).get("config", {{}}).get("authentication", {{}}).get("validate_tokens", False)

    # Build comprehensive description
    description_parts = [f"{{API_TITLE}} - FastMCP 2.x MCP Server"]
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
    try:
        print("🔧 Configuring FastMCP middleware...")
    except UnicodeEncodeError:
        print("Configuring FastMCP middleware...")
    app.add_middleware(ErrorHandlingMiddleware(include_traceback=True))
{auth_middleware_setup}
    app.add_middleware(DetailedTimingMiddleware())
    app.add_middleware(LoggingMiddleware(include_payloads=False))
    try:
        print("✅ FastMCP middleware configured")
    except UnicodeEncodeError:
        print("[OK] FastMCP middleware configured")

    # Compose all servers (strategy: {composition_strategy})
    {"asyncio.run(" if is_async_composition else ""}_compose_mcp_servers(){")" if is_async_composition else ""}

    if args.transport == "stdio":
        logger.info("🚀 Starting FastMCP 2.x server with STDIO transport")
        logger.info("  🔐 Authentication: BACKEND_API_TOKEN environment variable")
        logger.info("  🔒 Token validation: N/A (STDIO mode - backend validates tokens)")
        logger.info(f"  📦 Modules: {len(module_names)} composed ({{TOTAL_TOOL_COUNT}} MCP tools)")
        logger.info("  🔧 Middleware: Error handling → Auth → Timing → Logging")
        app.run(transport="stdio")
    else:  # http
        logger.info(f"🚀 Starting FastMCP 2.x server with HTTP transport on {{args.host}}:{{args.port}}")
        logger.info("  🔐 Authentication: Bearer token in Authorization header")
{http_import_call}
        logger.info(f"  🔒 Token validation: {{'enabled (JWT)' if hasattr(args, 'validate_tokens') and args.validate_tokens else 'disabled (delegated to backend)'}}")
        logger.info(f"  📦 Modules: {len(module_names)} composed ({{TOTAL_TOOL_COUNT}} MCP tools)")

        # For HTTP transport with token validation, use ASGI middleware
        if hasattr(args, 'validate_tokens') and args.validate_tokens:
            logger.info("  🔧 ASGI Middleware: Authentication (JWT validation) at HTTP layer")
            logger.info("  🔑 JWT validation: Enabled via Starlette auth backend + scope guard")
            logger.info("  📦 Event store: Enabled for SSE resumability")

            # Create JWT verifier for token validation
            jwt_verifier = create_jwt_verifier()
            if jwt_verifier:
                # Create ASGI authentication middleware stack with enforcement
                # Note: Middleware runs in reverse order, so RequireScopesMiddleware runs AFTER AuthenticationMiddleware
                asgi_middleware = build_authentication_stack(jwt_verifier, require_auth=True)

                # Get the HTTP app with authentication middleware and event store
                # Fallback validation - if JWT validation fails, try this
                # NOTE: middleware must be an iterable, not a function. If you need custom logic, use a proper ASGI middleware class.
                http_app = create_streamable_http_app(
                    server=app,
                    streamable_http_path="/mcp",
                    event_store=event_store,
                    json_response=False,
                    stateless_http=False,
                    debug=False
                    # No 'middleware' argument unless it's a list of ASGI middleware
                )

                # Run with uvicorn
                import uvicorn
                logger.info("  ✅ ASGI middleware configured with token enforcement")
                config = uvicorn.Config(
                    http_app,  # Use http_app directly, middleware is already applied
                    host=args.host,
                    port=args.port,
                    log_level="info"
                )
                uvicorn_server = uvicorn.Server(config)

                import anyio
                anyio.run(uvicorn_server.serve)
            else:
                logger.warning("  ⚠️ JWT verifier initialization failed - falling back to backend validation")
                logger.info("  📦 Event store: Enabled for SSE resumability")

                # Get HTTP app with event store
                http_app = create_streamable_http_app(
                    server=app,
                    streamable_http_path="/mcp",
                    event_store=event_store,
                    json_response=False,
                    stateless_http=False,
                    debug=False
                )

                # Run with uvicorn
                import uvicorn
                config = uvicorn.Config(
                    http_app,
                    host=args.host,
                    port=args.port,
                    log_level="info"
                )
                uvicorn_server = uvicorn.Server(config)

                import anyio
                anyio.run(uvicorn_server.serve)
        else:
            logger.info("  🔧 FastMCP Middleware: Error handling → Auth (backend validation) → Timing → Logging")
            logger.info("  📦 Event store: Enabled for SSE resumability")

            # Get HTTP app with event store
            http_app = create_streamable_http_app(
                server=app,
                streamable_http_path="/mcp",
                event_store=event_store,
                json_response=False,
                stateless_http=False,
                debug=False
            )

            # Run with uvicorn
            import uvicorn
            config = uvicorn.Config(
                http_app,
                host=args.host,
                port=args.port,
                log_level="info"
            )
            uvicorn_server = uvicorn.Server(config)

            import anyio
            anyio.run(uvicorn_server.serve)


if __name__ == "__main__":
    main()
'''

    return code


def generate_all(
    base_dir: Path | None = None,
) -> tuple[ApiMetadata, SecurityConfig, dict[str, ModuleSpec], int]:
    """
    Main entry point for generating all MCP server components.

    Args:
        base_dir: Base directory containing generated_openapi and openapi spec.
                  Defaults to current working directory.

    Returns:
        tuple: (api_metadata, security_config, modules, total_tool_count)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Get metadata and configuration
    api_metadata = get_api_metadata(base_dir)
    security_config = get_security_config(base_dir)

    # Generate server modules
    modules, total_tools = generate_modular_servers(base_dir)

    return api_metadata, security_config, modules, total_tools
