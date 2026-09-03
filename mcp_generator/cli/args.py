"""Command-line argument definitions."""

import argparse

from ..config import DEFAULT_FASTMCP_TARGET, PROJECT_REPO_URL
from ..fastmcp_target import SUPPORTED_TARGETS


def build_parser() -> argparse.ArgumentParser:
    """Build the generate-mcp argument parser."""
    parser = argparse.ArgumentParser(
        description="MCP Generator 4.x - OpenAPI to FastMCP 4 Server Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Basic generation (minimal server)
  generate-mcp

  # With custom OpenAPI file
  generate-mcp --file ./my-api-spec.yaml

  # Download from URL
  generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

  # With optional features
  generate-mcp --enable-storage --enable-caching
  generate-mcp --enable-resources
  generate-mcp --enable-apps
  generate-mcp --enable-apps --generate-ui

  # Enrich descriptions with an overlay or auto-enhance
  generate-mcp --overlay ./my-overlay.yaml
  generate-mcp --overlay fhir --schema-depth 5
  generate-mcp --auto-overlay

  # Generate A2A agent adapter
  generate-mcp --enable-a2a

Optional Features (disabled by default for simplicity):
  --enable-storage    Persistent storage for OAuth tokens & state
  --enable-caching    Response caching (reduces API calls)
  --enable-resources  MCP resources from GET endpoints
  --enable-apps       MCP Apps with interactive UI display tools
  --generate-ui       API-specific display tools from response schemas (requires --enable-apps)
  --overlay FILE      Apply OpenAPI Overlay 1.0.0 to enrich descriptions
  --auto-overlay      Auto-generate rule-based overlay for AI-friendly descriptions
  --enable-a2a        Generate A2A agent adapter + AgentCard

Documentation: {PROJECT_REPO_URL}
        """,
    )

    parser.add_argument(
        "--file",
        type=str,
        default="./openapi.json",
        help="Path to OpenAPI specification file (default: ./openapi.json)",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL to download OpenAPI specification from (overrides --file)",
    )

    parser.add_argument(
        "--enable-storage",
        action="store_true",
        default=False,
        help="Enable persistent storage backend (for OAuth tokens, session state, user data)",
    )

    parser.add_argument(
        "--enable-caching",
        action="store_true",
        default=False,
        help="Enable response caching middleware (reduces backend API calls, requires --enable-storage)",
    )

    parser.add_argument(
        "--enable-resources",
        action="store_true",
        default=False,
        help="Generate MCP resource templates from GET endpoints (exposes API data as resources)",
    )

    parser.add_argument(
        "--enable-apps",
        action="store_true",
        default=False,
        help="Generate MCP Apps display tools (interactive tables, charts, forms) and optional GenerativeUI",
    )

    parser.add_argument(
        "--generate-ui",
        action="store_true",
        default=False,
        help="Generate API-specific display tools from OpenAPI response schemas (requires --enable-apps)",
    )

    parser.add_argument(
        "--schema-depth",
        type=int,
        default=3,
        help="Max nesting depth for response schema parsing (default: 3, increase for deeply nested APIs)",
    )

    parser.add_argument(
        "--overlay",
        type=str,
        default=None,
        help="Overlay name or path. Bundled: 'fhir'. Or a path to an Overlay 1.0.0 file",
    )

    parser.add_argument(
        "--auto-overlay",
        action="store_true",
        default=False,
        help="Auto-generate a rule-based overlay to enhance API descriptions for AI agents",
    )

    parser.add_argument(
        "--enable-a2a",
        action="store_true",
        default=False,
        help="Generate A2A (Agent-to-Agent) adapter and AgentCard for multi-agent orchestration",
    )

    parser.add_argument(
        "--fastmcp-target",
        type=int,
        choices=SUPPORTED_TARGETS,
        default=DEFAULT_FASTMCP_TARGET,
        help=(
            "FastMCP major version the generated server targets "
            f"(default: {DEFAULT_FASTMCP_TARGET}). 4 is a prerelease target: it drops "
            "server-side sampling and replaces elicitation with a guard response, "
            "which the sessionless 2026-07-28 protocol requires"
        ),
    )

    return parser
