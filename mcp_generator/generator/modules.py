"""Generates one server module per API tag."""

from pathlib import Path

from ..fastmcp_target import FastMCPTarget
from ..introspection import (
    get_api_modules,
    get_body_schemas,
    get_resource_endpoints,
)
from ..models import ModuleSpec
from ..renderers import generate_server_module


def generate_modular_servers(
    base_dir: Path | None = None,
    enable_resources: bool = False,
    target: FastMCPTarget | None = None,
) -> tuple[dict[str, ModuleSpec], int]:
    """Generate modular MCP servers from API client classes.

    Args:
        base_dir: Base directory containing generated_openapi. Defaults to current working directory.
        enable_resources: Generate MCP resource templates from GET endpoints
        target: FastMCP major version matrix to generate against

    Returns:
        tuple[dict[str, ModuleSpec], int]: (dict of modules keyed by module_name, total_tool_count)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Get API modules dynamically (sort keys for deterministic output)
    api_modules = get_api_modules(base_dir)

    # Get request body schemas for form data coercion (flat → nested)
    body_schemas = get_body_schemas(base_dir)

    # Get resource endpoints if enabled
    resources_by_tag = {}
    if enable_resources:
        resources_by_tag = get_resource_endpoints(base_dir)

    servers: dict[str, ModuleSpec] = {}
    total_tools = 0

    # Track method names already generated across modules to avoid duplicates.
    # When an OpenAPI operation has multiple tags, openapi-generator places the
    # same method on every corresponding API class.  We use first-tag-wins:
    # the first module (alphabetical) that contains a method claims it.
    seen_methods: set[str] = set()

    # Generate a server module for each API class. Key the resulting dict by
    # ModuleSpec.module_name (stable identifier) rather than filename to avoid
    # brittle filename-based lookups downstream.
    for api_var_name in sorted(api_modules.keys()):
        api_class = api_modules[api_var_name]

        # Find matching resource endpoints for this API by tag
        # Map api_var_name (e.g., 'pet_api') to tag (e.g., 'pet')
        tag_name = api_var_name.replace("_api", "")
        resource_endpoints = resources_by_tag.get(tag_name, [])

        module_spec = generate_server_module(
            api_var_name,
            api_class,
            resource_endpoints,
            exclude_methods=seen_methods,
            body_schemas=body_schemas,
            target=target,
        )
        servers[module_spec.module_name] = module_spec
        total_tools += module_spec.tool_count

    return servers, total_tools
