"""Renders pyproject.toml and fastmcp.json for a generated server."""

from typing import Any

from ..config import TEMPLATES_DIR
from ..fastmcp_target import FastMCPTarget, resolve_target


def render_pyproject_template(
    api_metadata: Any,
    security_config: Any,
    server_name: str,
    total_tools: int,
    enable_storage: bool = False,
    enable_apps: bool = False,
    target: FastMCPTarget | None = None,
) -> str:
    """Render the pyproject.toml template with provided values."""
    target = target or resolve_target()
    template_path = TEMPLATES_DIR / "pyproject_template.toml"
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    # Remove any non-comment, non-section-header lines at the top (defensive, in case template is changed)

    lines = template.splitlines()
    cleaned_lines = []
    found_section = False
    for line in lines:
        if line.strip() == "" or line.strip().startswith("#"):
            cleaned_lines.append(line)
        elif line.strip().startswith("["):
            cleaned_lines.append(line)
            found_section = True
        elif not found_section:
            # skip accidental junk at the very top (before first section)
            continue
        else:
            cleaned_lines.append(line)
    template = "\n".join(cleaned_lines)

    # Sanitize version to be PEP 440 compliant
    raw_version = str(getattr(api_metadata, "version", "0.1.0"))
    # Replace invalid dots in local version with + (e.g., 1.0.0.abc123 -> 1.0.0+abc123)
    # PEP 440: local version must use + separator, not .
    import re

    # Match pattern: major.minor.patch followed by optional pre-release, then .something
    # Convert the last dot before local version identifier to +
    version_match = re.match(r"^(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?)\.([\w]+)$", raw_version)
    if version_match:
        # Has invalid dot before local version - fix it
        sanitized_version = f"{version_match.group(1)}+{version_match.group(2)}"
    else:
        # Check for multiple trailing segments with dots (e.g., 1.0.0-alpha.123.abc.def)
        # Replace last occurrence of dot followed by non-numeric with +
        sanitized_version = re.sub(
            r"\.([a-zA-Z]\w*)$",  # Last dot followed by identifier starting with letter
            r"+\1",
            raw_version,
        )

    # Build dependencies list
    dependencies = [
        target.dependency_pin(enable_apps=enable_apps),
        "openapi-py-fetch>=0.3.0",
        "httpx>=0.23.0",
        target.pydantic_pin,
        "python-dateutil>=2.8.2",
        "urllib3>=2.0.0,<3.0.0",
        "typing-extensions>=4.7.1",
        "python-jose[cryptography]>=3.3.0,<4.0.0",
        "uvicorn>=0.20.0",
        "anyio>=3.6.0",
        "annotated-types>=0.4.0",
    ]

    # Add cryptography for storage encryption if storage is enabled
    if enable_storage:
        dependencies.append("cryptography>=42.0.0")

    packages = ["servers"]
    if enable_apps:
        packages.append("apps")
    if security_config.has_authentication():
        packages.insert(1, "middleware")
    # Render template
    # Clean description: single-line, escape quotes, remove newlines/markdown
    raw_description = getattr(api_metadata, "description", "MCP Server")
    # Remove newlines and excessive whitespace
    clean_description = " ".join(raw_description.split())
    # Escape double quotes
    clean_description = clean_description.replace('"', "'")
    # Truncate if too long (TOML recommends short descriptions)
    if len(clean_description) > 200:
        clean_description = clean_description[:197] + "..."

    # Render dependencies as TOML array: each line is a quoted string ending with a comma
    dependencies_toml = "\n    ".join([f'"{dep}",' for dep in dependencies])
    return (
        template.replace("{{project_name}}", server_name.replace("_", "-").replace(".", "-"))
        .replace("{{version}}", sanitized_version)
        .replace("{{description}}", clean_description)
        .replace("{{dependencies}}", dependencies_toml)
        .replace("{{script_name}}", f"{server_name}-mcp")
        .replace("{{main_module}}", f"{server_name}_mcp_generated")
        .replace("{{entry_point}}", server_name)
        .replace('packages = ["servers"]', f"packages = {packages}")
    )


def render_fastmcp_template(
    api_metadata: Any,
    security_config: Any,
    modules: dict[str, Any],
    total_tools: int,
    server_name: str,
    enable_apps: bool = False,
) -> str:
    """Render the fastmcp.json template with provided values."""
    import json

    template_path = TEMPLATES_DIR / "fastmcp_template.json"
    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    # Build service name from API title
    from ..utils import sanitize_server_name

    service_name = sanitize_server_name(api_metadata.title).replace("_", "-")

    # Determine auth settings from security config
    # Only enable JWT validation for bearer schemes or authorizationCode OAuth2 flows
    has_bearer = security_config and security_config.bearer_format
    has_auth_code = (
        security_config
        and security_config.oauth_config
        and "authorizationCode" in security_config.oauth_config.flows
    )
    validate_tokens = "true" if (has_bearer or has_auth_code) else "false"

    rendered = (
        template.replace("{{composition_strategy}}", "mount")
        .replace("{{resource_prefix_format}}", "path")
        .replace("{{validate_tokens}}", validate_tokens)
        .replace("{{service_name}}", f"{service_name}-mcp")
    )

    # Auto-populate oauth_proxy when an authorizationCode flow is detected
    if security_config and security_config.oauth_config:
        auth_code_flow = security_config.oauth_config.flows.get("authorizationCode")
        if auth_code_flow:
            parsed = json.loads(rendered)
            oauth_proxy = parsed["features"]["oauth_proxy"]
            oauth_proxy["enabled"] = True
            if auth_code_flow.authorization_url:
                oauth_proxy["upstream_authorization_endpoint"] = auth_code_flow.authorization_url
            if auth_code_flow.token_url:
                oauth_proxy["upstream_token_endpoint"] = auth_code_flow.token_url
            if auth_code_flow.scopes:
                oauth_proxy["valid_scopes"] = list(auth_code_flow.scopes.keys())
            rendered = json.dumps(parsed, indent=2) + "\n"

    # Auto-enable apps feature when --enable-apps is set
    if enable_apps:
        parsed = json.loads(rendered)
        parsed["features"]["apps"]["enabled"] = True
        rendered = json.dumps(parsed, indent=2) + "\n"

    return rendered
