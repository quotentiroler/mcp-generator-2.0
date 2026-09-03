# Installation

## Prerequisites

- **Python 3.11+** — required for modern type hints and features
- **OpenAPI Specification** — your API's OpenAPI 3.0.x, 3.1.x, or Swagger 2.0 spec (JSON or YAML)

!!! note "Pure Python"
    MCP Generator is 100% Python — no Java, Node.js, or other runtimes needed.

## Install from PyPI (Recommended)

```bash
pip install mcp-generator

# Or with uv
uv pip install mcp-generator

# Verify installation
generate-mcp --help
```

## Install from Source

If you want to contribute or run the latest development version:

```bash
git clone https://github.com/quotentiroler/mcp-generator-4.x.git
cd mcp-generator-4.x

# With uv
uv sync

# Or with pip
pip install -e .

# Verify installation
generate-mcp --help
```

## Verify Installation

You should see output similar to:

```
usage: generate-mcp [-h] [--file FILE] [--url URL] [--enable-storage]
                    [--enable-caching] [--enable-resources]
...
```

## Next Steps

Head to the [Quick Start](quickstart.md) to generate your first MCP server.
