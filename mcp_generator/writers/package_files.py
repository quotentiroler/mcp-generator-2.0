"""Writes README, pyproject.toml, Docker and package init files."""

from pathlib import Path
from typing import Any

from ..fastmcp_target import FastMCPTarget
from ..models import ModuleSpec


def write_package_files(
    output_dir: Path,
    api_metadata: Any,
    security_config: Any,
    modules: dict[str, ModuleSpec],
    total_tools: int,
    enable_storage: bool = False,
    enable_apps: bool = False,
    target: FastMCPTarget | None = None,
) -> None:
    """Write package metadata files (README, pyproject.toml, __init__.py)."""

    from ..utils import sanitize_server_name

    # Generate README.md
    oauth_flows = (
        ", ".join(security_config.oauth_config.flows.keys())
        if security_config.oauth_config
        else "None"
    )
    server_name = sanitize_server_name(api_metadata.title)

    # Build header with optional icon
    header = f"# {api_metadata.title} - MCP Server\n\n"
    if api_metadata.icon_emoji:
        header = f"# {api_metadata.icon_emoji} {api_metadata.title} - MCP Server\n\n"
    elif api_metadata.icon_url:
        header = f"# {api_metadata.title} - MCP Server\n\n"
        header += f'<img src="{api_metadata.icon_url}" alt="API Logo" height="64">\n\n'

    readme_content = (
        header
        + f"""Auto-generated Model Context Protocol (MCP) server for {api_metadata.title}.

**Version:** {api_metadata.version}

## Overview

This MCP server provides {total_tools} tools across {len(modules)} modules, enabling AI agents
to interact with the {api_metadata.title} API through the Model Context Protocol.

### Features
```- ✅ **{total_tools} API Tools** - Complete coverage of backend API operations
- ✅ **OAuth2 Authentication** - Support for {oauth_flows}
- ✅ **JWT Token Validation** - Secure token verification
- ✅ **Modular Architecture** - {len(modules)} independent server modules
- ✅ **SSE Support** - Server-Sent Events for streaming responses
- ✅ **Session Management** - Stateful HTTP sessions with event store
- ✅ **Tool Tags** - Automatic per-module tag grouping (FastMCP 3.1)
- ✅ **Tool Timeouts** - Configurable per-tool timeout (default 30s)
- ✅ **SearchTools** - BM25 text search over tool catalog (opt-in via fastmcp.json)
- ✅ **CodeMode** - Experimental meta-tool transform (opt-in via fastmcp.json)
- ✅ **ResponseLimitingMiddleware** - Safe UTF-8 truncation of oversized responses
- ✅ **PingMiddleware** - HTTP keepalive for long-lived connections
- ✅ **MultiAuth** - Compose multiple token verifiers (opt-in via fastmcp.json)
- ✅ **Component Versioning** - Deprecated endpoints annotated automatically
- ✅ **Dynamic Visibility** - Per-session component toggling via scopes (opt-in)
- ✅ **OpenTelemetry** - Tracing with MCP semantic conventions (opt-in via fastmcp.json)

## Generated Modules

"""
    )

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
export API_TOKEN="your-token-here"
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

- `API_BASE_URL` - Backend API URL (default: {api_metadata.backend_url})
- `API_TOKEN` - API token for STDIO mode

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
- Uses `API_TOKEN` environment variable
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

### Adding FastMCP Middleware

The generated server uses FastMCP 2.13+ and supports additional middleware for caching, rate limiting, and more.

#### Response Caching Middleware (Recommended for Production)

Add FastMCP's built-in caching to improve performance:

```python
# In your {server_name}_mcp_generated.py, before app.run():
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from key_value.aio.stores.disk import DiskStore

app.add_middleware(ResponseCachingMiddleware(
    cache_storage=DiskStore(directory="cache"),
    list_tools_settings={{"ttl": 300}},      # 5 minutes
    call_tool_settings={{"ttl": 3600}},       # 1 hour
    read_resource_settings={{"ttl": 3600}}    # 1 hour
))
```

For distributed deployments, use Redis:

```python
# Requires: pip install 'py-key-value-aio[redis]'
from key_value.aio.stores.redis import RedisStore

app.add_middleware(ResponseCachingMiddleware(
    cache_storage=RedisStore(host="redis.example.com", port=6379),
    call_tool_settings={{"ttl": 3600}}
))
```

See the FastMCP docs for more options: https://docs.fastmcp.com/servers/middleware/#caching-middleware

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

    # --- Use template for pyproject.toml ---
    from ..renderers import render_pyproject_template

    pyproject_content = render_pyproject_template(
        api_metadata=api_metadata,
        security_config=security_config,
        server_name=server_name,
        total_tools=total_tools,
        enable_storage=enable_storage,
        enable_apps=enable_apps,
        target=target,
    )
    pyproject_file = output_dir / "pyproject.toml"
    with open(pyproject_file, "w", encoding="utf-8") as f:
        f.write(pyproject_content)
    print("   ✅ pyproject.toml")

    # --- Use template for fastmcp.json ---
    from ..renderers import render_fastmcp_template

    fastmcp_content = render_fastmcp_template(
        api_metadata=api_metadata,
        security_config=security_config,
        modules=modules,
        total_tools=total_tools,
        server_name=server_name,
        enable_apps=enable_apps,
    )
    fastmcp_file = output_dir / "fastmcp.json"
    with open(fastmcp_file, "w", encoding="utf-8") as f:
        f.write(fastmcp_content)
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
    from ..templates.dockerfile_template import (
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
