# MCP Generator 2.0

**🚀 OpenAPI to FastMCP 2.x Server Generator**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-Notes:

- The registry file lives at ~/.mcp-generator/servers.json by default
- Override registry location: Set MCP_REGISTRY_PATH env var or use XDG_DATA_HOME/mcp-generator/servers.json
- run-mcp forwards these flags to the generated server's entry point.
- You can also run the generated script directly: python <name>_mcp_generated.py

#### Internal registry (local)

Use register-mcp to quickly create a local internal registry of MCP servers you generate. Entries live in ~/.mcp-generator/servers.json; add/list/remove in seconds, and run-mcp lets you start servers by name. You can run multiple servers side‑by‑side (e.g., different HTTP ports) for a smooth developer workflow.

**Registry location priority:**
1. `MCP_REGISTRY_PATH` environment variable (explicit override)
2. `XDG_DATA_HOME/mcp-generator/servers.json` (XDG Base Directory spec)
3. `~/.mcp-generator/servers.json` (default)

**JSON output for automation:**
```bash
# Get registry as JSON for scripting
uv run register-mcp list --json | jq '.petstore.version'
```

**Export for publishing:**
```bash
# Generate server.json template for MCP Registry
uv run register-mcp export my_server -o server.json
# Edit TODO fields, then publish with mcp-publisher CLI
```e.svg)](https://www.python.org/downloads/)
[![FastMCP 2.x](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://github.com/jlowin/fastmcp)

Transform any OpenAPI specification into a production-ready Model Context Protocol (MCP) server with enterprise-grade authentication, modular architecture, and comprehensive middleware support.

---

## 🎯 Overview

MCP Generator 2.0 is an advanced code generator that automatically creates FastMCP 2.x servers from OpenAPI 3.0.x/3.1.x specifications. It bridges REST APIs and AI agents by generating fully-functional MCP tools that AI assistants like Claude, ChatGPT, and others can use to interact with your APIs.

### Supported OpenAPI Versions

- ✅ **OpenAPI 3.0.x** - Fully supported (recommended)
- ✅ **OpenAPI 3.1.x** - Fully supported
- ❌ **Swagger 2.0** - Not supported (please upgrade to OpenAPI 3.0+)

> **Note**: Both JSON and YAML formats are supported. The generator uses OpenAPI Generator CLI under the hood, which handles both formats seamlessly.

## 🏆 Why MCP Generator 2.0?

| Feature                     | MCP Generator 2.0                          | Typical Generators         |
| --------------------------- | ------------------------------------------ | -------------------------- |
| **Architecture**      | Modular, composable sub-servers            | Monolithic single file     |
| **Authentication**    | JWT validation with JWKS, OAuth2 flows     | Basic token passing        |
| **Middleware System** | Full FastMCP 2.x middleware stack          | Limited or none            |
| **Scalability**       | One module per API class                   | All operations in one file |
| **Type Safety**       | Full Pydantic model support                | Basic validation           |
| **Testing**           | Auto-generated test suites                 | Manual testing only        |
| **Observability**     | Timing, logging, error handling middleware | Basic logging              |
| **Event Store**       | Resumable SSE with event persistence       | Simple SSE                 |
| **Production Ready**  | ✅ Yes                                     | ⚠️ Often prototypes      |

---

## 📦 Installation

### Prerequisites

- **Python 3.11+**: Required for modern type hints and features
- **uv** (recommended) or **pip**: For dependency management
- **Node.js & npm**: Required for OpenAPI Generator CLI
- **OpenAPI Specification**: Your API's OpenAPI 3.0.x or 3.1.x spec file (JSON or YAML)

### Install with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/quotentiroler/mcp-generator-2.0.git
cd mcp-generator-2.0

# Install dependencies
uv sync

# Verify installation
uv run generate-mcp --help
```

### Install with pip

```bash
# Clone the repository
git clone https://github.com/quotentiroler/mcp-generator-2.0.git
cd mcp-generator-2.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
generate-mcp --help
```

### Install OpenAPI Generator

```bash
# Using npm (recommended)
npm install -g @openapitools/openapi-generator-cli

# Verify installation
npx @openapitools/openapi-generator-cli version
```

---

## 🚀 Quick Start

### 1. Generate MCP Server from OpenAPI Spec

```bash
# Using local file (default: ./openapi.json)
uv run generate-mcp

# Using custom file
uv run generate-mcp --file ./my-api-spec.yaml

# Download from URL
uv run generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json
```

**What happens:**

- ✅ Generates Python API client from OpenAPI spec
- ✅ Creates modular MCP server modules
- ✅ Generates authentication middleware
- ✅ Creates OAuth2 provider
- ✅ Writes package files and tests
- ✅ Outputs to `generated_mcp/` directory

### 2. Register Your MCP Server

```bash
# Register the generated server
uv run register-mcp ./generated_mcp

# Verify registration
uv run run-mcp --list
```

This adds your server to the local registry at `~/.mcp-generator/servers.json` so you can easily run it by name.

### 3. Run Your MCP Server

```bash
# Option 1: Run via registry (STDIO mode for local AI clients)
export BACKEND_API_TOKEN="your-api-token-here"  # On Windows: set BACKEND_API_TOKEN=...
uv run run-mcp swagger_petstore_openapi

# Option 2: Run via registry (HTTP mode)
uv run run-mcp swagger_petstore_openapi --mode http --port 8000

# Option 3: Run directly with Python
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport stdio

# Option 4: Run with FastMCP CLI (uses fastmcp.json config)
cd generated_mcp
uv run fastmcp run fastmcp.json
# Or: fastmcp run fastmcp.json (if FastMCP is installed globally)
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
        "BACKEND_API_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

---

## 🧰 CLI reference

This project installs three CLI commands. Here’s a quick cheatsheet.

### generate-mcp

- Description: Generate a FastMCP 2.x server from an OpenAPI 3.0.x/3.1.x spec.
- Options:
  - --file <path>  Path to spec file (default: ./openapi.json)
  - --url <url>    Download spec from URL (overrides --file)
- Examples:

```bash
# Use local file (default)
uv run generate-mcp

# Custom file
uv run generate-mcp --file ./my-api.yaml

# From URL
uv run generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json
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
uv run register-mcp add ./generated_mcp

# Add (implicit)
uv run register-mcp ./generated_mcp

# List registered servers
uv run register-mcp list

# List as JSON
uv run register-mcp list --json

# Remove by name
uv run register-mcp remove swagger_petstore_openapi

# Export server metadata for publishing
uv run register-mcp export swagger_petstore_openapi -o server.json
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
uv run run-mcp --list

# Run via STDIO (Linux/macOS)
export BACKEND_API_TOKEN="your-api-token" && uv run run-mcp swagger_petstore_openapi

# Run via STDIO (Windows PowerShell)
powershell
$env:BACKEND_API_TOKEN = "your-api-token"
uv run run-mcp swagger_petstore_openapi

# Run via HTTP
uv run run-mcp swagger_petstore_openapi --mode http --port 8000

# HTTP with JWT validation
uv run run-mcp swagger_petstore_openapi --mode http --port 8000 --validate-tokens
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
python main_mcp_generated.py --transport http --validate-tokens
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
uv run generate-mcp --file openapi.yaml

# Validate OpenAPI spec
uv run python scripts/validate_openapi.py

# Generate JWT keypair for testing
uv run python scripts/generate_jwt_keypair.py
```

---

## 📚 Examples

### Example 1: Swagger Petstore

```bash
# Generate from Petstore API
uv run generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# Run the server
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py
```

### Example 2: GitHub API

```bash
# Download GitHub OpenAPI spec
uv run generate-mcp --url https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json

# Outputs: 300+ tools for GitHub API operations
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to contribute:

### Reporting Bugs

1. Check existing issues: https://github.com/quotentiroler/mcp-generator-2.0/issues
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

Apache 2.0 is a permissive license that promotes wide adoption while providing patent protection. It's business-friendly, widely accepted by enterprises, and commonly used for development tools and code generators. This license allows you to use MCP Generator 2.0 in your projects without worrying about copyleft requirements.

**Generated Code:** The code generated by this tool is NOT considered a derivative work of the generator itself. You may license your generated MCP servers however you choose.

For the full license text, see [LICENSE](LICENSE) or visit https://www.apache.org/licenses/LICENSE-2.0

---

## 🙏 Acknowledgments

- **FastMCP**: Built on the excellent [FastMCP 2.x](https://github.com/jlowin/fastmcp) framework
- **OpenAPI Generator**: Uses [OpenAPI Generator](https://openapi-generator.tech/) for client generation
- **Model Context Protocol**: Implements the [MCP specification](https://modelcontextprotocol.io/)
- **Anthropic**: For the MCP standard and Claude Desktop integration

---

If you find this project useful, please consider giving it a star! ⭐

It helps others discover the tool and motivates continued development.

<div align="center">

**Made with ❤️**

[Report Bug](https://github.com/quotentiroler/mcp-generator-2.0/issues) · [Request Feature](https://github.com/quotentiroler/mcp-generator-2.0/issues) · [Documentation](https://github.com/quotentiroler/mcp-generator-2.0/wiki)

</div>
