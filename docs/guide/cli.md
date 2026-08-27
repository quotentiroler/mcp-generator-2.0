# CLI Reference

MCP Generator installs three CLI commands.

## generate-mcp

Generate a FastMCP 3.x server from an OpenAPI spec.

```bash
generate-mcp [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--file <path>` | `./openapi.json` | Path to OpenAPI spec file (JSON or YAML) |
| `--url <url>` | — | Download spec from URL (overrides `--file`) |
| `--enable-storage` | off | Enable persistent storage backend |
| `--enable-caching` | off | Enable response caching (requires `--enable-storage`) |
| `--enable-resources` | off | Expose GET endpoints as MCP resources |
| `--fastmcp-target <3\|4>` | `3` | FastMCP major version the generated server targets |

### FastMCP target version

Generated servers target FastMCP 3.x by default. Pass `--fastmcp-target 4` to emit
for FastMCP 4, which is built on the MCP Python SDK v2 and serves the sessionless
`2026-07-28` protocol. FastMCP 4 is still a prerelease, so the flag pins it exactly
and prints a warning.

Three things differ in the emitted server:

| Concern | Target 3 | Target 4 |
|---|---|---|
| Missing required parameters | `ctx.elicit()` asks the client | Tool returns what it needs — elicitation cannot reach a client that negotiates the modern protocol |
| API error recovery | `ctx.sample()` asks the caller's model for a hint | Error is raised on its own — server-side sampling is removed in 4.x |
| HTTP client | `httpx` | `httpx2` — FastMCP 4 replaced httpx across its whole stack |

Installing a target-4 server needs prereleases enabled for the FastMCP packages
only. Constrain them rather than passing `--prerelease=allow`, which opts your
entire dependency graph into prereleases:

```toml
[tool.uv]
constraint-dependencies = ["fastmcp-slim==4.0.0b3"]
```

### Examples

```bash
# Local file (default)
generate-mcp

# Custom file
generate-mcp --file ./my-api.yaml

# From URL
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# Target FastMCP 4 (prerelease)
generate-mcp --file ./openapi.json --fastmcp-target 4

# All features enabled
generate-mcp --url https://example.com/api.json \
  --enable-storage --enable-caching --enable-resources
```

---

## register-mcp

Manage the local server registry at `~/.mcp-generator/servers.json`.

```bash
register-mcp <COMMAND> [OPTIONS]
```

### Commands

| Command | Description |
|---|---|
| `add <path>` | Register a generated server (default when a path is given) |
| `list` | Show all registered servers |
| `remove <name>` | Unregister a server by name |
| `export <name>` | Export server metadata as `server.json` |

### Options

| Option | Command | Description |
|---|---|---|
| `--json` | `list` | Output as JSON for scripting |
| `-o, --output <file>` | `export` | Write to file (default: stdout) |

### Examples

```bash
# Register (explicit)
register-mcp add ./generated_mcp

# Register (shorthand)
register-mcp ./generated_mcp

# List registered servers
register-mcp list

# List as JSON
register-mcp list --json

# Remove
register-mcp remove swagger_petstore_openapi

# Export metadata
register-mcp export swagger_petstore_openapi -o server.json
```

---

## run-mcp

Run a registered server by name.

```bash
run-mcp <SERVER_NAME> [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--list` | — | List registered servers and exit |
| `--mode` / `--transport` | `stdio` | Transport mode: `stdio` or `http` |
| `--host` | `0.0.0.0` | HTTP host |
| `--port` | `8000` | HTTP port |
| `--validate-tokens` | off | Enable JWT validation (HTTP mode) |

### Examples

```bash
# List servers
run-mcp --list

# Run via STDIO
export API_TOKEN="your-token"
run-mcp swagger_petstore_openapi

# Run via HTTP
run-mcp swagger_petstore_openapi --mode http --port 8000

# HTTP with JWT validation
run-mcp swagger_petstore_openapi --mode http --port 8000 --validate-tokens
```

### Notes

- The registry lives at `~/.mcp-generator/servers.json`
- `run-mcp` forwards flags to the generated server's entry point
- You can also run the generated script directly: `python <name>_mcp_generated.py`
