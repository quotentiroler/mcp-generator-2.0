"""
File writing utilities.

Handles writing generated code to the filesystem, creating directories,
and managing package initialization files.
"""

from pathlib import Path

from .models import ModuleSpec
from .utils import normalize_version


def write_server_modules(modules: dict[str, ModuleSpec], output_dir: Path) -> None:
    """Write server modules to the filesystem."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # Write each server module
    for module_spec in modules.values():
        output_file = output_dir / module_spec.filename
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(module_spec.code)
        print(f"   ✅ {module_spec.filename}")

    # Generate __init__.py for servers package
    imports = []
    exports = []

    for module_spec in modules.values():
        module_name = module_spec.filename.replace(".py", "")
        server_var = f"{module_name.replace('_server', '')}_mcp"
        imports.append(f"from .{module_name} import mcp as {server_var}")
        exports.append(f'    "{server_var}",')

    init_content = '"""Servers package for modular MCP servers."""\n'
    init_content += "\n".join(imports) + "\n\n"
    init_content += "__all__ = [\n"
    init_content += "\n".join(exports) + "\n"
    init_content += "]\n"

    init_file = output_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(init_content)
    print("   ✅ __init__.py")


def write_middleware_files(
    middleware_code: str, oauth_code: str, event_store_code: str, output_dir: Path
) -> None:
    """Write middleware files to the filesystem."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # Write authentication middleware
    auth_file = output_dir / "authentication.py"
    with open(auth_file, "w", encoding="utf-8") as f:
        f.write(middleware_code)
    print("   ✅ authentication.py")

    # Write OAuth provider
    oauth_file = output_dir / "oauth_provider.py"
    with open(oauth_file, "w", encoding="utf-8") as f:
        f.write(oauth_code)
    print("   ✅ oauth_provider.py")

    # Write event store
    event_store_file = output_dir / "event_store.py"
    with open(event_store_file, "w", encoding="utf-8") as f:
        f.write(event_store_code)
    print("   ✅ event_store.py")

    # Create __init__.py for middleware package
    init_file = output_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Middleware package for MCP server."""\n')
        f.write(
            "from .authentication import ApiClientContextMiddleware, JWTAuthenticationBackend, AuthenticatedIdentity\n"
        )
        f.write(
            "from .oauth_provider import build_authentication_stack, create_remote_auth_provider, create_jwt_verifier, RequireScopesMiddleware\n"
        )
        f.write("from .event_store import InMemoryEventStore\n")
        f.write("\n__all__ = [\n")
        f.write('    "ApiClientContextMiddleware",\n')
        f.write('    "JWTAuthenticationBackend",\n')
        f.write('    "AuthenticatedIdentity",\n')
        f.write('    "build_authentication_stack",\n')
        f.write('    "create_remote_auth_provider",\n')
        f.write('    "create_jwt_verifier",\n')
        f.write('    "RequireScopesMiddleware",\n')
        f.write('    "InMemoryEventStore",\n')
        f.write("]\n")


def write_main_server(code: str, output_file: Path) -> None:
    """Write main composition server to filesystem."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Generated main server: {output_file}")


def write_package_files(
    output_dir: Path,
    api_metadata,
    security_config,
    modules: dict[str, ModuleSpec],
    total_tools: int,
) -> None:
    """Write package metadata files (README, pyproject.toml, __init__.py)."""

    import re

    # Generate README.md
    oauth_flows = (
        ", ".join(security_config.oauth_config.flows.keys())
        if security_config.oauth_config
        else "None"
    )
    # Use same cleaning logic as in cli.py - remove version patterns from title
    clean_title = re.sub(r"\s+v?\d+\.\d+(\.\d+)?", "", api_metadata.title, flags=re.IGNORECASE)
    server_name = clean_title.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
    # Remove multiple consecutive underscores
    server_name = re.sub(r"_+", "_", server_name).strip("_")

    readme_content = f"""# {api_metadata.title} - MCP Server

Auto-generated Model Context Protocol (MCP) server for {api_metadata.title}.

**Version:** {api_metadata.version}

## Overview

This MCP server provides {total_tools} tools across {len(modules)} modules, enabling AI agents
to interact with the {api_metadata.title} API through the Model Context Protocol.

### Features

- ✅ **{total_tools} API Tools** - Complete coverage of backend API operations
- ✅ **OAuth2 Authentication** - Support for {oauth_flows}
- ✅ **JWT Token Validation** - Secure token verification
- ✅ **Modular Architecture** - {len(modules)} independent server modules
- ✅ **SSE Support** - Server-Sent Events for streaming responses
- ✅ **Session Management** - Stateful HTTP sessions with event store

## Generated Modules

"""

    for module_spec in modules.values():
        module_name = module_spec.api_var_name.replace("_api", "")
        readme_content += f"- **{module_name}** - {module_spec.tool_count} tools\n"

    readme_content += f"""
## Installation

### Option 1: Using fastmcp.json (Recommended)

The generated [`mcp-server/fastmcp.json`](mcp-server/fastmcp.json ) file provides standard configuration for FastMCP clients:

```bash
# Install using FastMCP CLI
fastmcp install mcp-json fastmcp.json

# Or copy configuration to your MCP client
# For Claude Desktop: ~/.claude/claude_desktop_config.json
# For Cursor: ~/.cursor/mcp.json
# For VS Code: .vscode/mcp.json
```

The [`mcp-server/fastmcp.json`](mcp-server/fastmcp.json ) file contains:
- 📋 Server metadata and capabilities
- 📦 Python dependencies
- 🔧 Environment variable requirements
- ⚙️ Middleware configuration
- 🔐 OAuth2 authentication details

### Option 2: Manual Installation

```bash
pip install -e .
```

Or with uv:
```bash
uv pip install -e .
```

## Usage

### Quick Start with FastMCP

If you have the FastMCP CLI installed:

```bash
# Run from fastmcp.json configuration
fastmcp run fastmcp.json

# Install to Claude Desktop
fastmcp install claude-desktop fastmcp.json

# Install to Cursor
fastmcp install cursor fastmcp.json
```

### Using the run-mcp Command

After installation, use the `run-mcp` command to start the server:

#### STDIO Mode (for local AI assistants)

```bash
run-mcp {server_name} --mode stdio
```

Set authentication token:
```bash
export BACKEND_API_TOKEN="your-token-here"
run-mcp {server_name} --mode stdio
```

#### HTTP Mode (for remote access)

```bash
run-mcp {server_name} --mode http --host 0.0.0.0 --port 8000
```

With JWT validation enabled:
```bash
run-mcp {server_name} --mode http --validate-tokens
```

#### Get Help

```bash
run-mcp --help
```

**Note:** You can configure `validate_tokens` in `fastmcp.json` under `middleware.config.authentication.validate_tokens` to avoid passing the flag every time.

### Direct Python Execution

You can also run the server directly with Python:

#### STDIO Mode

```bash
python {server_name}_mcp_generated.py --transport stdio
```

#### HTTP Mode

```bash
python {server_name}_mcp_generated.py --transport http --host 0.0.0.0 --port 8000 --validate-tokens
```

## Configuration

### fastmcp.json

The `fastmcp.json` file contains default configuration:

```json
{{
  "middleware": {{
    "config": {{
      "authentication": {{
        "validate_tokens": false  // Enable JWT validation for HTTP transport
      }}
    }}
  }}
}}
```

Set `validate_tokens: true` to enable JWT validation by default when using HTTP transport.

### Environment Variables

- `BACKEND_API_URL` - Backend API URL (default: {api_metadata.backend_url})
- `BACKEND_API_TOKEN` - API token for STDIO mode

**Note:** JWT validation is configured automatically from the OpenAPI specification. The JWKS URI, issuer, and audience are extracted during code generation and baked into the server code.

### Command Line Options

```
run-mcp <server_name> [OPTIONS]

Arguments:
  server_name              Name of the server to run

Options:
  --mode {{stdio|http}}      Transport protocol (default: stdio)
  --host HOST              Host to bind (HTTP mode, default: 0.0.0.0)
  --port PORT              Port to bind (HTTP mode, default: 8000)
  --validate-tokens        Enable JWT token validation (HTTP mode only)
  --help                   Show help message
```

Or using direct Python execution:

```
python {server_name}_mcp_generated.py [OPTIONS]

Options:
  --transport {{stdio|http}}  Transport protocol (default: stdio)
  --host HOST                Host to bind (HTTP mode, default: 0.0.0.0)
  --port PORT                Port to bind (HTTP mode, default: 8000)
  --validate-tokens          Enable JWT token validation (HTTP mode only)
```

## Authentication

### STDIO Mode
- Uses `BACKEND_API_TOKEN` environment variable
- Token passed to backend API for each request
- Token validation happens at the backend (not in MCP server)

### HTTP Mode
- Clients send `Authorization: Bearer <token>` header
- **Without `--validate-tokens`**: Tokens forwarded to backend for validation
- **With `--validate-tokens`**: MCP server validates JWT tokens using JWKS endpoint
- Session management via `mcp-session-id` header

## Development

This server is auto-generated from the OpenAPI specification.

### Regenerate

```bash
python -m mcp_generator
```

**⚠️ DO NOT EDIT MANUALLY** - Changes will be overwritten on regeneration.

## API Documentation

- **Backend URL:** {api_metadata.backend_url}
"""

    if api_metadata.external_docs and api_metadata.external_docs.get("url"):
        readme_content += f"- **Documentation:** {api_metadata.external_docs['url']}\n"

    if api_metadata.contact and api_metadata.contact.get("email"):
        readme_content += f"- **Contact:** {api_metadata.contact['email']}\n"

    if api_metadata.license and api_metadata.license.get("name"):
        readme_content += f"\n## License\n\n{api_metadata.license['name']}\n"

    readme_file = output_dir / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("   ✅ README.md")

    # Generate pyproject.toml
    # Sanitize package name: replace underscores with hyphens, remove dots
    package_name = server_name.replace("_", "-").replace(".", "-")
    normalized_version = normalize_version(api_metadata.version)

    pyproject_content = f"""# Auto-generated package configuration for {api_metadata.title}
# Generated by mcp_generator - DO NOT EDIT MANUALLY

[project]
name = "{package_name}-mcp"
version = "{normalized_version}"
description = "MCP Server for {api_metadata.title}"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.2.0,<3.0.0",  # mount() composition available since 2.2.0 (2.9.0+ for prefix-less mounting)
    "httpx>=0.23.0",  # HTTP client - we use basic AsyncClient/Client features (stable since 0.23)
    "pydantic>=2.0.0,<3.0.0",  # OpenAPI client uses Pydantic v2 models (AnyHttpUrl)
    "python-dateutil>=2.8.2",  # Date parsing for OpenAPI client
    "urllib3>=2.0.0,<3.0.0",  # OpenAPI client dependency
    "typing-extensions>=4.7.1",  # Type hints backport for Python 3.11+
    "python-jose[cryptography]>=3.3.0,<4.0.0",  # JWT handling (used by FastMCP's JWTVerifier)
    "uvicorn>=0.20.0",  # ASGI server - basic server functionality
    "anyio>=3.6.0",  # Async compatibility layer (FastMCP dependency)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
]

[project.scripts]
{package_name}-mcp = "{server_name}_mcp_generated:main"

[project.entry-points."mcp_servers"]
{server_name} = "{server_name}_mcp_generated:main"

[build-system]
requires = ["setuptools>=68.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
"""

    # Include necessary packages (servers and middleware if auth is enabled)
    # Note: openapi_client is imported via sys.path, not packaged with the MCP server
    packages_list = ['"servers"']
    if security_config.has_authentication():
        packages_list.insert(1, '"middleware"')  # Add middleware between servers and openapi_client

    pyproject_content += f"packages = [{', '.join(packages_list)}]\n"
    pyproject_content += f'py-modules = ["{server_name}_mcp_generated"]\n'

    pyproject_file = output_dir / "pyproject.toml"
    with open(pyproject_file, "w", encoding="utf-8") as f:
        f.write(pyproject_content)
    print("   ✅ pyproject.toml")

    # Add Hatchling config as a compatibility fallback for environments
    # that default to hatch/hatchling as the build backend. This mirrors
    # the setuptools package list so wheel builders can locate the
    # `servers` (and `middleware`) package directories.
    hatch_lines = [
        "\n# Hatchling build target (compatibility)\n",
        "[tool.hatch.build.targets.wheel]\n",
        "packages = [\n",
    ]
    # always include servers
    hatch_lines.append('  { include = "servers" },\n')
    if security_config.has_authentication():
        hatch_lines.append('  { include = "middleware" },\n')
    hatch_lines.append("]\n")

    # Append hatch config to pyproject.toml so environments using hatch won't
    # fail with the "Unable to determine which files to ship" error.
    with open(pyproject_file, "a", encoding="utf-8") as f:
        f.writelines(hatch_lines)
    print("   ✅ hatch build settings (compat) added to pyproject.toml")

    # Generate fastmcp.json
    main_server_file = output_dir / f"{server_name}_mcp_generated.py"

    # Get list of Python dependencies from pyproject.toml
    dependencies = [
        "fastmcp>=2.2.0,<3.0.0",  # mount() composition available since 2.2.0 (2.9.0+ for prefix-less mounting)
        "httpx>=0.23.0",  # HTTP client - we use basic AsyncClient/Client features (stable since 0.23)
        "pydantic>=2.0.0,<3.0.0",  # OpenAPI client uses Pydantic v2 models (AnyHttpUrl)
        "python-dateutil>=2.8.2",  # Date parsing for OpenAPI client
        "urllib3>=2.0.0,<3.0.0",  # OpenAPI client dependency
        "typing-extensions>=4.7.1",  # Type hints backport for Python 3.11+
        "python-jose[cryptography]>=3.3.0,<4.0.0",  # JWT handling (used by FastMCP's JWTVerifier)
        "uvicorn>=0.20.0",  # ASGI server - basic server functionality
        "anyio>=3.6.0",  # Async compatibility layer (FastMCP dependency)
    ]

    # Get middleware list
    middleware_list = ["error_handling", "authentication", "timing", "logging"]

    import json

    fastmcp_config = {
        "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
        "name": api_metadata.title,
        "version": normalized_version,
        "description": api_metadata.description or f"FastMCP 2.0 Server for {api_metadata.title}",
        "source": {"path": str(main_server_file.name), "entrypoint": "app"},
        "transport": {"type": "stdio", "defaultTransport": "stdio", "supports": ["stdio", "http"]},
        "environment": {
            "dependencies": dependencies,
            "requiredEnvVars": [
                {
                    "name": "BACKEND_API_TOKEN",
                    "description": "Bearer token for backend API authentication (STDIO mode)",
                    "required": False,
                },
                {
                    "name": "BACKEND_API_URL",
                    "description": f"Base URL for the backend API (defaults to {api_metadata.backend_url})",
                    "required": False,
                },
            ],
        },
        "middleware": {
            "enabled": middleware_list,
            "config": {
                "error_handling": {"include_traceback": True},
                "authentication": {"validate_tokens": False},
                "logging": {"include_payloads": False},
            },
        },
        "composition": {
            "strategy": "mount",
            "description": "mount: dynamic composition with live linking (recommended), import: static composition for better performance",
            "resource_prefix_format": "path",
            "description_format": "path: resource://prefix/path (FastMCP 2.4+), protocol: prefix+resource://path (legacy)",
        },
        "features": {"tools": total_tools, "resources": 0, "prompts": 0},
        "metadata": {
            "generator": "mcp_generator",
            "generated_from": "OpenAPI specification",
            "api_classes": len(modules),
            "fastmcp_version": "2.12.5",
            "backend_url": api_metadata.backend_url,
        },
    }

    # Add OAuth info if available
    if security_config.oauth_config:
        fastmcp_config["authentication"] = {
            "type": "oauth2",
            "flows": list(security_config.oauth_config.flows.keys()),
            "scopes": list(security_config.oauth_config.all_scopes.keys()),
        }

    fastmcp_file = output_dir / "fastmcp.json"
    with open(fastmcp_file, "w", encoding="utf-8") as f:
        json.dump(fastmcp_config, f, indent=2)
    print("   ✅ fastmcp.json")

    # Generate top-level __init__.py
    init_content = f'''"""
{api_metadata.title} - MCP Server

Auto-generated Model Context Protocol server.
Version: {api_metadata.version}

DO NOT EDIT MANUALLY - regenerate using: python -m mcp_generator
"""

__version__ = "{api_metadata.version}"
'''

    init_file = output_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(init_content)
    print("   ✅ __init__.py")

    # Generate Docker files
    from .templates.dockerfile_template import (
        generate_docker_compose,
        generate_dockerfile,
        generate_dockerignore,
    )

    dockerfile_content = generate_dockerfile(api_metadata, server_name)
    dockerfile = output_dir / "Dockerfile"
    with open(dockerfile, "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    print("   ✅ Dockerfile")

    # Generate docker-compose.yml
    docker_compose_content = generate_docker_compose(api_metadata, server_name)
    docker_compose_file = output_dir / "docker-compose.yml"
    with open(docker_compose_file, "w", encoding="utf-8") as f:
        f.write(docker_compose_content)
    print("   ✅ docker-compose.yml")

    # Generate .dockerignore
    dockerignore_content = generate_dockerignore()
    dockerignore_file = output_dir / ".dockerignore"
    with open(dockerignore_file, "w", encoding="utf-8") as f:
        f.write(dockerignore_content)
    print("   ✅ .dockerignore")


def write_test_files(auth_test_code: str | None, tool_test_code: str, test_dir: Path) -> None:
    """
    Write generated test files to the filesystem.

    Args:
        auth_test_code: Generated authentication flow test code (None if no auth)
        tool_test_code: Generated tool validation test code
        test_dir: Directory to write test files to
    """
    test_dir.mkdir(parents=True, exist_ok=True)

    # Write auth flow tests (only if auth is configured)
    if auth_test_code:
        auth_test_file = test_dir / "test_auth_flows_generated.py"
        with open(auth_test_file, "w", encoding="utf-8") as f:
            f.write(auth_test_code)
        print("   ✅ test_auth_flows_generated.py")

    # Write tool tests
    tool_test_file = test_dir / "test_tools_generated.py"
    with open(tool_test_file, "w", encoding="utf-8") as f:
        f.write(tool_test_code)
    print("   ✅ test_tools_generated.py")


def write_test_runner(test_runner_code: str, output_file: Path) -> None:
    """
    Write test runner script to filesystem.

    Args:
        test_runner_code: Generated test runner script code
        output_file: Path to write the test runner script
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(test_runner_code)

    # Make executable on Unix-like systems
    import stat

    current_permissions = output_file.stat().st_mode
    output_file.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"   ✅ {output_file.name}")
