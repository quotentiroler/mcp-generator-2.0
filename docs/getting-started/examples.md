# Examples

## Swagger Petstore

The classic test API — 19 endpoints across 3 tags.

```bash
generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport http --port 8000
```

**Generated structure:**

```
generated_mcp/
├── swagger_petstore_openapi_mcp_generated.py   # Main composition server
├── servers/
│   ├── pet.py                                   # Pet operations (8 tools)
│   ├── store.py                                 # Store operations (4 tools)
│   └── user.py                                  # User operations (7 tools)
├── middleware/
│   └── authentication.py                        # Auth middleware
├── fastmcp.json                                 # FastMCP configuration
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## GitHub API

A large-scale spec — 300+ endpoints.

```bash
generate-mcp --url https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json
```

This generates 300+ tools organized into modular sub-servers by tag (repos, issues, pulls, actions, etc.).

## Minimal API

A two-endpoint API to understand the basics.

```bash
cd examples/minimal
generate-mcp --file openapi.json
```

See the [examples/](https://github.com/quotentiroler/mcp-generator-4.x/tree/main/examples) directory for pre-generated outputs you can inspect.

## Running the Examples

Each example directory contains:

- `openapi.json` — the source spec
- `generated_mcp/` — pre-generated output
- `generated_openapi/` — generated Python API client
- `test/` — test runner

```bash
# Run any example's tests
cd examples/petstore
uv run python test/run_tests.py
```
