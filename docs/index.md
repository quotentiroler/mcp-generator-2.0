---
hide:
  - navigation
---

# MCP Generator 4.x

**Transform any OpenAPI specification into a production-ready [FastMCP 3.x](https://github.com/PrefectHQ/fastmcp) server.**

[![PyPI](https://img.shields.io/pypi/v/mcp-generator)](https://pypi.org/project/mcp-generator/)
[![GitHub Release](https://img.shields.io/github/v/release/quotentiroler/mcp-generator-3.x?label=version)](https://github.com/quotentiroler/mcp-generator-3.x/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-v3.11-3776ab.svg)](https://www.python.org/downloads/)
[![FastMCP 3.x](https://img.shields.io/badge/FastMCP-3.x-green.svg)](https://github.com/PrefectHQ/fastmcp)

---

## What is MCP Generator?

MCP Generator automatically creates **modular, composable MCP servers** from OpenAPI 3.0.x, 3.1.x, and Swagger 2.0 specifications. It bridges REST APIs and AI agents by generating fully-functional MCP tools that AI assistants like Claude, ChatGPT, and others can use to interact with your APIs.

## Key Features

<div class="grid cards" markdown>

-   :material-view-module:{ .lg .middle } **Modular Architecture**

    ---

    One sub-server per API tag — composable, scalable, and organized.

-   :material-shield-lock:{ .lg .middle } **Enterprise Auth**

    ---

    JWT/JWKS validation, OAuth2 flows, MultiAuth composition, scope enforcement.

-   :material-layers:{ .lg .middle } **Middleware Stack**

    ---

    Error handling, timing, logging, response limiting, ping keepalive — full FastMCP 3.x pipeline.

-   :material-magnify:{ .lg .middle } **SearchTools & CodeMode**

    ---

    FastMCP 3.1 transforms: BM25 tool discovery and experimental meta-tool execution.

-   :material-chart-timeline:{ .lg .middle } **OpenTelemetry**

    ---

    Built-in tracing with MCP semantic conventions — Console or OTLP export.

-   :material-test-tube:{ .lg .middle } **Auto-Generated Tests**

    ---

    Test suites generated alongside your server — ready to run out of the box.

-   :material-docker:{ .lg .middle } **Docker Ready**

    ---

    Dockerfile and docker-compose generated for instant containerized deployment.

-   :material-tag-multiple:{ .lg .middle } **Tool Tags & Timeouts**

    ---

    Automatic per-module tags, configurable timeouts, deprecated endpoint detection.

</div>

## Quick Example

```bash
# Install from PyPI
pip install mcp-generator

# Generate from any OpenAPI spec
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# Run it
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport http --port 8000
```

That's it — a fully functional MCP server with 19 tools, modular sub-servers, authentication middleware, and auto-generated tests.

## Supported Specs

| Format | Status |
|---|---|
| OpenAPI 3.0.x | :white_check_mark: Fully supported |
| OpenAPI 3.1.x | :white_check_mark: Fully supported |
| Swagger 2.0 | :white_check_mark: Fully supported |
| JSON | :white_check_mark: |
| YAML | :white_check_mark: |

## Next Steps

- [**Installation**](getting-started/installation.md) — set up the generator in 2 minutes
- [**Quick Start**](getting-started/quickstart.md) — generate your first MCP server
- [**Architecture**](guide/architecture.md) — understand the generated code structure
- [**Comparison**](comparison.md) — see how we compare to alternatives
