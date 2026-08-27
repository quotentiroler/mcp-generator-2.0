"""Top-level entry point tying introspection to generation."""

from pathlib import Path

from ..fastmcp_target import FastMCPTarget
from ..introspection import (
    get_api_metadata,
    get_security_config,
)
from ..models import ApiMetadata, ModuleSpec, SecurityConfig
from .modules import generate_modular_servers


def generate_all(
    base_dir: Path | None = None,
    enable_resources: bool = False,
    target: FastMCPTarget | None = None,
) -> tuple[ApiMetadata, SecurityConfig, dict[str, ModuleSpec], int]:
    """
    Main entry point for generating all MCP server components.

    Args:
        base_dir: Base directory containing generated_openapi and openapi spec.
                  Defaults to current working directory.
        enable_resources: Generate MCP resource templates from GET endpoints
        target: FastMCP major version matrix to generate against

    Returns:
        tuple: (api_metadata, security_config, modules, total_tool_count)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Get metadata and configuration
    api_metadata = get_api_metadata(base_dir)
    security_config = get_security_config(base_dir)

    # Generate server modules with optional resources
    modules, total_tools = generate_modular_servers(
        base_dir, enable_resources=enable_resources, target=target
    )

    return api_metadata, security_config, modules, total_tools
