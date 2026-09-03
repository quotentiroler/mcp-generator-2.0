# MCP Generator 4.x

**🚀 OpenAPI to FastMCP 4 Server Generator**

[![PyPI](https://img.shields.io/pypi/v/mcp-generator)](https://pypi.org/project/mcp-generator/)
[![GitHub Release](https://img.shields.io/github/v/release/quotentiroler/mcp-generator-3.x?label=version)](https://github.com/quotentiroler/mcp-generator-3.x/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-v3.11-3776ab.svg)](https://www.python.org/downloads/)
[![FastMCP 3.x](https://img.shields.io/badge/FastMCP-3.x-green.svg)](https://github.com/PrefectHQ/fastmcp)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://quotentiroler.github.io/mcp-generator-3.x/)

Transform any OpenAPI specification into a production-ready Model Context Protocol (MCP) server with enterprise-grade authentication, modular architecture, and comprehensive middleware support.

---

## 🎯 Overview

MCP Generator 4.x is an advanced code generator that automatically creates FastMCP 3.x servers from OpenAPI 3.0.x/3.1.x specifications. It bridges REST APIs and AI agents by generating fully-functional MCP tools that AI assistants like Claude, ChatGPT, and others can use to interact with your APIs.

### Supported OpenAPI Versions

- ✅ **OpenAPI 3.0.x** - Fully supported (recommended)
- ✅ **OpenAPI 3.1.x** - Fully supported
- ✅ **Swagger 2.0** - Fully supported

> **Note**: Both JSON and YAML formats are supported. The generator includes a pure Python OpenAPI client generator — no Java or Node.js required.

## 🏆 Why MCP Generator 4.x?

| Feature                     | MCP Generator 4.x                          | Typical Generators         |
| --------------------------- | ------------------------------------------ | -------------------------- |
| **Architecture**      | Modular, composable sub-servers            | Monolithic single file     |
| **Authentication**    | JWT validation with JWKS, OAuth2 flows     | Basic token passing        |
| **Middleware System** | Full FastMCP 3.x middleware stack          | Limited or none            |
| **Scalability**       | One module per API class                   | All operations in one file |
| **Type Safety**       | Full Pydantic model support                | Basic validation           |
| **Testing**           | Auto-generated test suites                 | Manual testing only        |
| **Observability**     | Timing, logging, error handling middleware | Basic logging              |
| **Tag Discovery**     | Auto-discovers undeclared API tags          | Manual tag mapping         |
| **Event Store**       | Resumable SSE with event persistence       | Simple SSE                 |
| **MCP Apps**          | Interactive UI display tools (tables, charts, forms) | None                 |
| **Production Ready**  | ✅ Yes                                     | ⚠️ Often prototypes      |

### Competitive Comparison

How MCP Generator 4.x stacks up against every other OpenAPI-to-MCP project on GitHub (updated April 2026):

| Feature | [**MCP Generator 4.x**](https://github.com/quotentiroler/mcp-generator-3.x) (Py, 18★) | [openapi-mcp-server](https://github.com/janwilmake/openapi-mcp-server) (TS, 887★) | [mcp-link](https://github.com/automation-ai-labs/mcp-link) (Go, 602★) | [openapi-mcp-generator](https://github.com/harsha-iiiv/openapi-mcp-generator) (TS, 566★) | [openapi-mcp](https://github.com/ckanthony/openapi-mcp) (Go, 183★) | [openapi-mcp-codegen](https://github.com/cnoe-io/openapi-mcp-codegen) (Py, 35★) |
|---|---|---|---|---|---|---|
| **Approach** | Code generation | Runtime search/proxy | Runtime proxy | Code generation | Runtime proxy (Docker) | Code generation |
| **OpenAPI 3.0** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OpenAPI 3.1** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Swagger 2.0** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Modular sub-servers** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **FastMCP 4 native** | ✅ | ❌ | N/A | ❌ | N/A | ❌ |
| **Streamable HTTP** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **JWT / JWKS auth** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **OAuth2 flows** | ✅ | ❌ | header injection | env vars only | ❌ | header injection |
| **Middleware stack** | ✅ (timing, logging, cache, auth) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MCP Resources** | ✅ (GET endpoints) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Event Store** | ✅ (resumable) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Auto-generated tests** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (eval suite) |
| **MCP Apps (UI)** | ✅ (tables, charts, forms) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **A2A agent generation** | ✅ (lightweight a2a-sdk) | ❌ | ❌ | ❌ | ❌ | ✅ (LangGraph) |
| **LLM-enhanced docs** | ✅ (OpenAPI Overlay 1.0) | ❌ | ❌ | ❌ | ❌ | ✅ (OpenAPI Overlay) |
| **Docker output** | ✅ | ❌ | ❌ | ❌ | ✅ (primary) | ✅ |
| **Tag auto-discovery** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Server registry** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Endpoint filtering** | tag-based | ❌ | path filters | x-mcp extension | tag/op filters | ❌ |
| **Schema validation** | Pydantic | ❌ | ❌ | Zod | ❌ | ❌ |
| **Actively maintained** | ✅ (Apr 2026) | ⚠️ (Feb 2026) | ❌ (Apr 2025) | ✅ (Mar 2026) | ⚠️ (Mar 2026) | ❌ (Nov 2025) |

> **Note**: [mcpo](https://github.com/open-webui/mcpo) (4,027★) solves the **inverse** problem — exposing MCP servers as OpenAPI endpoints — and is complementary rather than competitive.

---

## ✨ FastMCP 3.x Features

MCP Generator 4.x leverages all the latest FastMCP 3.x capabilities:

| Feature | Description |
|---------|-------------|
| **Tool Tags** | Automatic per-module tag grouping (`@mcp.tool(tags=["pet"])`) |
| **Tool Timeouts** | Configurable per-tool timeout (default 30s) |
| **SearchTools** | BM25 text search over tool catalog (opt-in via `fastmcp.json`) |
| **CodeMode** | Experimental meta-tool transform (opt-in via `fastmcp.json`) |
| **ResponseLimitingMiddleware** | UTF-8-safe truncation of oversized responses (1MB default) |
| **PingMiddleware** | HTTP keepalive for long-lived connections |
| **MultiAuth** | Compose multiple token verifiers (JWT + OAuth2, etc.) |
| **Component Versioning** | Deprecated OpenAPI endpoints annotated automatically |
| **Dynamic Visibility** | Per-session component toggling via scopes |
| **OpenTelemetry** | Tracing with MCP semantic conventions (Console/OTLP export) |
| **validate_output** | FastMCP output validation support |

All features are configurable via the generated `fastmcp.json`:

```json
{
  "features": {
    "search_tools": { "enabled": false },
    "code_mode": { "enabled": false },
    "response_limiting": { "enabled": true, "max_size_bytes": 1048576 },
    "ping_middleware": { "enabled": true },
    "opentelemetry": { "enabled": false, "service_name": "my-api-mcp" }
  }
}
```

---

## 📦 Installation

### Prerequisites

- **Python 3.11+**: Required for modern type hints and features
- **OpenAPI Specification**: Your API's OpenAPI 3.0.x or 3.1.x spec file (JSON or YAML)

### Install from PyPI (Recommended)

```bash
pip install mcp-generator

# Or with uv
uv pip install mcp-generator

# Verify installation
generate-mcp --help
```

### Install from Source

```bash
git clone https://github.com/quotentiroler/mcp-generator-3.x.git
cd mcp-generator-3.x
uv sync   # or: pip install -e .

# Verify installation
generate-mcp --help
```

---

## 🚀 Quick Start

### 1. Generate MCP Server from OpenAPI Spec

```bash
# Using local file (default: ./openapi.json)
generate-mcp

# Using custom file
generate-mcp --file ./my-api-spec.yaml

# Download from URL
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json
```

**What happens:**

- ✅ Generates Python API client from OpenAPI spec
- ✅ Auto-discovers undeclared tags from API paths (tag auto-discovery)
- ✅ Creates modular MCP server modules
- ✅ Generates authentication middleware
- ✅ Creates OAuth2 provider
- ✅ Writes package files and tests
- ✅ Outputs to `generated_mcp/` directory

#### Optional Features (Disabled by Default)

By default, the generator creates a minimal, production-ready server. Enable additional features as needed:

```bash
# Enable persistent storage (for OAuth tokens, session state)
generate-mcp --enable-storage

# Enable response caching (reduces backend API calls)
generate-mcp --enable-storage --enable-caching

# Enable MCP resources (expose API data as resources)
generate-mcp --enable-resources

# Enable MCP Apps (interactive UI: tables, charts, forms, detail views)
generate-mcp --enable-apps

# Enable MCP Apps with API-specific display tools from response schemas
generate-mcp --enable-apps --generate-ui

# Enable all features
generate-mcp --enable-storage --enable-caching --enable-resources --enable-apps --generate-ui

# Apply an OpenAPI Overlay to enhance descriptions before generation
generate-mcp --overlay my-overlay.yaml

# Auto-generate an overlay from the spec (no manual file needed)
generate-mcp --auto-overlay

# Generate an A2A agent card and adapter alongside the MCP server
generate-mcp --enable-a2a
```

**Available Features:**

| Flag | Description | When to Use |
|------|-------------|-------------|
| `--enable-storage` | Persistent storage backend | OAuth refresh tokens, session data, user preferences |
| `--enable-caching` | Response caching with TTL | Rate-limited APIs, expensive operations, slow endpoints |
| `--enable-resources` | MCP resource templates | Expose API data for context/retrieval (GET endpoints) |
| `--enable-apps` | MCP Apps with interactive UI display tools | Rich tables, charts, forms, and detail views in MCP clients |
| `--generate-ui` | API-specific display tools from response schemas | Auto-generated UI per endpoint (requires `--enable-apps`) |
| `--enable-a2a` | A2A agent card + adapter | Expose your MCP server as an A2A-compatible agent |
| `--overlay PATH` | Apply an OpenAPI Overlay file | Enhance descriptions, add examples before generation |
| `--auto-overlay` | Auto-generate an overlay from the spec | Quick enrichment without writing an overlay by hand |

> **Note**: `--enable-caching` requires `--enable-storage` as it uses the storage backend for cache persistence.

**Why disabled by default?**
- Keeps generated code simple and focused
- Fewer dependencies to manage
- Easier to understand and customize
- Most APIs work perfectly without these features

The generator will show which features are available at the end of generation with a copy-paste command to re-generate with features enabled.

💡 **Tip**: Run `generate-mcp --help` to see all available options and examples.

### 2. Register Your MCP Server

```bash
# Register the generated server
register-mcp ./generated_mcp

# Verify registration
run-mcp --list
```

This adds your server to the local registry at `~/.mcp-generator/servers.json` so you can easily run it by name.

### 3. Run Your MCP Server

```bash
# Option 1: Run via registry (STDIO mode for local AI clients)
export API_TOKEN="your-api-token-here"  # On Windows: set API_TOKEN=...
run-mcp swagger_petstore_openapi

# Option 2: Run via registry (HTTP mode)
run-mcp swagger_petstore_openapi --mode http --port 8000

# Option 3: Run directly with Python
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport stdio

# Option 4: Run with FastMCP CLI
cd generated_mcp
# Note: Use :create_server to properly compose the server
fastmcp run swagger_petstore_openapi_mcp_generated.py:create_server
# Or with fastmcp.json config:
fastmcp run fastmcp.json
```

### 4. Use with AI Clients

#### Claude Desktop (STDIO Mode)

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": ["/path/to/generated_mcp/swagger_petstore_openapi_mcp_generated.py"],
      "env": {
        "API_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

---

## 🔍 Testing with MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official debugging tool for MCP servers. It provides both a visual UI and CLI mode for testing your generated servers.

### Quick Start with Inspector

```bash
# Generate your MCP server first
generate-mcp --file ./openapi.json

# Test with Inspector using FastMCP (recommended)
cd generated_mcp
fastmcp dev swagger_petstore_openapi_mcp_generated.py:create_server

# Or test directly with Python
npx @modelcontextprotocol/inspector python swagger_petstore_openapi_mcp_generated.py

# Or use environment variables
npx @modelcontextprotocol/inspector -e API_TOKEN=your-token python swagger_petstore_openapi_mcp_generated.py
```

> **Note**: When using `fastmcp dev` or `fastmcp run`, always include `:create_server` to properly compose the modular server architecture.

The Inspector will:
- 🚀 Start your MCP server
- 🌐 Open a browser UI at `http://localhost:6274`
- 🔗 Connect via proxy at `http://localhost:6277`
- 🔑 Generate a secure session token

### Inspector Features for Your Generated Servers

**🛠️ Tool Testing**
- List all available tools generated from your OpenAPI spec
- Interactive form-based parameter input
- Real-time response visualization with JSON formatting
- Test OAuth2 authentication flows

**📦 Resource Exploration**
- Browse API resources hierarchically
- View resource metadata and content
- Test resource subscriptions

**💬 Prompt Testing**
- Interactive prompt sampling
- Streaming response visualization
- Compare multiple prompt variations

**📊 Debugging**
- Request/response history
- Visualized error messages
- Real-time server notifications
- Network timing information

### CLI Mode for Automation

Perfect for CI/CD and rapid development cycles:

```bash
# List available tools
npx @modelcontextprotocol/inspector --cli python swagger_petstore_openapi_mcp_generated.py --method tools/list

# Call a specific tool
npx @modelcontextprotocol/inspector --cli python swagger_petstore_openapi_mcp_generated.py \
  --method tools/call \
  --tool-name create_pet \
  --tool-arg 'name=Fluffy' \
  --tool-arg 'status=available'

# Test with environment variables
npx @modelcontextprotocol/inspector --cli \
  -e API_TOKEN=your-token \
  python swagger_petstore_openapi_mcp_generated.py \
  --method tools/list
```

### Testing HTTP/SSE Transports

If your generated server runs in HTTP mode:

```bash
# Start your server in HTTP mode
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport http --port 8000

# Connect Inspector to running server (SSE transport)
npx @modelcontextprotocol/inspector http://localhost:8000/sse

# Or use Streamable HTTP transport
npx @modelcontextprotocol/inspector http://localhost:8000/mcp --transport http
```

### Export Configuration

The Inspector can export your server configuration for use in Claude Desktop or other MCP clients:

1. **Server Entry Button** - Copies a single server config to clipboard
2. **Servers File Button** - Copies complete `mcp.json` structure

Example exported config:
```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": ["swagger_petstore_openapi_mcp_generated.py"],
      "env": {
        "API_TOKEN": "your-token"
      }
    }
  }
}
```

### Development Workflow

Integrate Inspector into your development cycle:

```bash
# 1. Generate server from OpenAPI spec
generate-mcp --file ./openapi.yaml

# 2. Test with Inspector UI (interactive development)
cd generated_mcp
npx @modelcontextprotocol/inspector -e API_TOKEN=test python *_mcp_generated.py

# 3. Automated testing (CI/CD)
npx @modelcontextprotocol/inspector --cli \
  -e API_TOKEN=test \
  python *_mcp_generated.py \
  --method tools/list > tools.json

# 4. Test specific tools
npx @modelcontextprotocol/inspector --cli \
  -e API_TOKEN=test \
  python *_mcp_generated.py \
  --method tools/call \
  --tool-name get_user \
  --tool-arg 'user_id=123'
```

### Tips for Testing Generated Servers

- **JWT Validation**: Use Inspector to test JWT authentication flows with `--validate-tokens`
- **OAuth2 Flows**: Inspector supports bearer token auth for testing OAuth2
- **Scope Testing**: Verify scope enforcement in your OAuth2 configuration
- **Error Handling**: Inspector visualizes error responses and stack traces
- **Performance**: Use Inspector's timing metrics to identify slow operations

For more details, see the [Inspector documentation](https://github.com/modelcontextprotocol/inspector).

---

## 🎨 MCP Apps — Interactive UI Display Tools

MCP Apps bring rich, interactive UI to MCP tool responses. Instead of returning raw JSON, your tools render as tables, charts, forms, and detail views in supported MCP clients.

### How It Works

1. **`--enable-apps`** adds curated, API-agnostic display tools (`show_table`, `show_detail`, `show_chart`, `show_form`, `show_comparison`) that the LLM fills with data from any API response
2. **`--generate-ui`** additionally introspects your OpenAPI response schemas and generates **per-endpoint display tools** (e.g., `show_pet_table`, `show_pet_detail`) with columns, badges, and data types pre-configured

```bash
# Curated display tools only (works with any API)
generate-mcp --enable-apps

# + API-specific display tools auto-generated from response schemas
generate-mcp --enable-apps --generate-ui
```

### Display Tool Types

| Tool | Description | Use Case |
|------|-------------|----------|
| `show_table` | Interactive data table with sortable columns | List endpoints, search results |
| `show_detail` | Card layout with key-value fields and badges | Single-record views (user profile, order details) |
| `show_chart` | Line, bar, area, and pie charts | Analytics, metrics, time-series data |
| `show_form` | Input form with validation | Create/update operations |
| `show_comparison` | Side-by-side comparison cards | Comparing records or options |

### Requirements

MCP Apps requires `prefab-ui` (the FastMCP Apps rendering library):

```bash
pip install "fastmcp[apps]"
```

If `prefab-ui` is not installed, display tools gracefully fall back to returning structured JSON — no runtime errors.

---

## 🧰 CLI reference

This project installs three CLI commands. Here's a quick cheatsheet.

### generate-mcp

- Description: Generate a FastMCP 3.x server from an OpenAPI 3.0.x/3.1.x spec.
- Options:
  - --file <path>  Path to spec file (default: ./openapi.json)
  - --url <url>    Download spec from URL (overrides --file)
- Examples:

```bash
# Use local file (default)
generate-mcp

# Custom file
generate-mcp --file ./my-api.yaml

# From URL
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json
```

### register-mcp

- Description: Manage the local registry at ~/.mcp-generator/servers.json
- Subcommands:
  - add <path>     Register a generated server (default when passing a path)
  - list           Show all registered servers
    - --json       Output as JSON for scripting/automation
  - remove <name>  Unregister a server by name
  - export <name>  Export server metadata as server.json for MCP Registry publishing
    - -o, --output <file>  Write to file (default: stdout)
- Examples:

```bash
# Add (explicit)
register-mcp add ./generated_mcp

# Add (implicit)
register-mcp ./generated_mcp

# List registered servers
register-mcp list

# List as JSON
register-mcp list --json

# Remove by name
register-mcp remove swagger_petstore_openapi

# Export server metadata for publishing
register-mcp export swagger_petstore_openapi -o server.json
```

### run-mcp

- Description: Run a registered server by name.
- Flags:
  - --list                 List registered servers and exit
  - --mode/--transport     stdio | http (default: stdio)
  - --host                 HTTP host (default: 0.0.0.0)
  - --port                 HTTP port (default: 8000)
  - --validate-tokens      Enable JWT validation (HTTP mode)
- Examples:

```bash
# List servers
run-mcp --list

# Run via STDIO (Linux/macOS)
export API_TOKEN="your-api-token" && run-mcp swagger_petstore_openapi

# Run via STDIO (Windows PowerShell)
powershell
$env:API_TOKEN = "your-api-token"
run-mcp swagger_petstore_openapi

# Run via HTTP
run-mcp swagger_petstore_openapi --mode http --port 8000

# HTTP with JWT validation
run-mcp swagger_petstore_openapi --mode http --port 8000 --validate-tokens
```

Notes:

- The registry file lives at ~/.mcp-generator/servers.json
- run-mcp forwards these flags to the generated server’s entry point.
- You can also run the generated script directly: python <name>_mcp_generated.py

#### Internal registry (local)

Use register-mcp to quickly create a local internal registry of MCP servers you generate. Entries live in ~/.mcp-generator/servers.json; add/list/remove in seconds, and run-mcp lets you start servers by name. You can run multiple servers side‑by‑side (e.g., different HTTP ports) for a smooth developer workflow.

#### Publish to a self-hosted MCP Registry

You can run your own MCP Registry (open source) and publish your generated servers to it:

- Deploy the official Registry service on your infra (Docker Compose/Kubernetes). Configure TLS, database (PostgreSQL), and a public base URL.
- Configure authentication/ownership verification: either set up GitHub OAuth/OIDC in the Registry, or use DNS/HTTP challenges to prove domain ownership for your namespace.
- Make your MCP server reachable over HTTP and provide valid server metadata (server.json) per the Registry schema.
- Use the publisher CLI to point at your Registry’s base URL, authenticate, and publish your server. After validation, it becomes discoverable via your Registry’s API/UI.

Note: This project does not (yet) auto-publish. The local per-user registry (~/.mcp-generator/servers.json) is for development convenience; publishing to a central catalog is an optional, separate step.

## OAuth2 Support

Automatically generates OAuth2 provider when OpenAPI spec contains OAuth2 security schemes.

**Supported Flows:**

- Implicit flow
- Authorization code flow
- Client credentials flow
- Password flow

**Features:**

- Scope extraction and validation
- Token introspection
- JWKS-based JWT verification
- Scope enforcement middleware

### JWT Validation

When `--validate-tokens` is enabled:

1. **Token Extraction**: Extracts JWT from `Authorization` header
2. **JWKS Discovery**: Auto-discovers JWKS endpoint from OpenAPI spec or uses standard well-known path
3. **Signature Verification**: Validates JWT signature using public key
4. **Claims Validation**: Checks expiration, issuer, audience
5. **Scope Enforcement**: Verifies required scopes for operations
6. **Identity Injection**: Makes user identity available to tools

**Configuration:**

The JWKS URI, issuer, and audience are **automatically extracted** from your OpenAPI specification's security schemes during generation. If not specified in the OpenAPI spec, sensible defaults are used:

- **JWKS URI**: `{backend_url}/.well-known/jwks.json`
- **Issuer**: `{backend_url}`
- **Audience**: `backend-api`

Simply enable JWT validation when running:

```bash
python server_generated.py --transport http --validate-tokens
```

Or set as default in `fastmcp.json`:

```json
{
  "middleware": {
    "config": {
      "authentication": {
        "validate_tokens": true
      }
    }
  }
}
```

**Note:** All JWT configuration is baked into the generated code - no environment variables needed!

---

## ⚙️ Configuration

### Tool Name Customization

Edit `mcp_generator/config.py`:

```python
# Abbreviations for long names
TOOL_NAME_ABBREVIATIONS = {
    'healthcare': 'hc',
    'organization': 'org',
}

# Complete overrides
TOOL_NAME_OVERRIDES = {
    'list_healthcare_users_by_role': 'list_users_by_role',
    'create_smart_app_registration': 'register_smart_app',
}

# Maximum tool name length (MCP/OpenAI limit)
MAX_TOOL_NAME_LENGTH = 64
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy mcp_generator/
```

### Project Commands

```bash
# Generate MCP server from example
generate-mcp --file openapi.yaml

# Validate OpenAPI spec
python mcp_generator/scripts/validate_openapi.py

# Generate JWT keypair for testing
python mcp_generator/scripts/generate_jwt_keypair.py
```

---

## 📚 Examples

### Example 1: Swagger Petstore

```bash
# Generate from Petstore API
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# Run the server
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py
```

### Example 2: GitHub API

```bash
# Download GitHub OpenAPI spec
generate-mcp --url https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json

# Outputs: 300+ tools for GitHub API operations
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to contribute:

### Reporting Bugs

1. Check existing issues: https://github.com/quotentiroler/mcp-generator-3.x/issues
2. Create detailed bug report with:
   - OpenAPI spec (sanitized/minimal example)
   - Full error message and stack trace
   - Steps to reproduce
   - Expected vs actual behavior

### Suggesting Features

1. Open a feature request issue
2. Describe the use case and benefit
3. Provide examples if applicable

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `uv run pytest`
5. Format code: `uv run ruff format .`
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Development Guidelines

- Follow existing code style (Ruff formatting)
- Add tests for new features
- Update documentation as needed
- Keep commits focused and descriptive

---

## 📄 License

This project is licensed under the **Apache License 2.0**.

### What This Means:

✅ **You can:**

- Use this software for any purpose (commercial or non-commercial)
- Modify the source code
- Distribute the software
- Include it in proprietary software
- Use it in SaaS applications
- Patent protection is granted

⚠️ **You must:**

- Include the original license and copyright notice
- State significant changes made to the code
- Include a copy of the Apache 2.0 license in your distribution

❌ **You cannot:**

- Use the project's trademarks without permission
- Hold the authors liable

### Why Apache 2.0?

Apache 2.0 is a permissive license that promotes wide adoption while providing patent protection. It's business-friendly, widely accepted by enterprises, and commonly used for development tools and code generators. This license allows you to use MCP Generator 4.x in your projects without worrying about copyleft requirements.

**Generated Code:** The code generated by this tool is NOT considered a derivative work of the generator itself. You may license your generated MCP servers however you choose.

For the full license text, see [LICENSE](LICENSE) or visit https://www.apache.org/licenses/LICENSE-2.0

---

## 🙏 Acknowledgments

- **FastMCP**: Built on the excellent [FastMCP 3.x](https://github.com/PrefectHQ/fastmcp) framework
- **OpenAPI Generator**: Uses [OpenAPI Generator](https://openapi-generator.tech/) for client generation
- **Model Context Protocol**: Implements the [MCP specification](https://modelcontextprotocol.io/)
- **Anthropic**: For the MCP standard and Claude Desktop integration

---

If you find this project useful, please consider giving it a star! ⭐

It helps others discover the tool and motivates continued development.

<div align="center">

**Made with ❤️**

[Report Bug](https://github.com/quotentiroler/mcp-generator-3.x/issues) · [Request Feature](https://github.com/quotentiroler/mcp-generator-3.x/issues) · [Documentation](https://quotentiroler.github.io/mcp-generator-3.x/)

</div>
