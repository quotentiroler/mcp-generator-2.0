# Middleware

Every generated server includes a configurable middleware stack built on FastMCP 4's native middleware pipeline.

## Default Middleware Stack

The following middleware is always included:

```
Request → Error Handling → Authentication → Timing → Logging → Response Limiting → Ping → Tool Execution
```

```python
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.rate_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.ping import PingMiddleware
from middleware.authentication import ApiClientContextMiddleware

# Middleware stack (order matters!)
app.add_middleware(ErrorHandlingMiddleware(include_traceback=True))
app.add_middleware(ApiClientContextMiddleware(...))
app.add_middleware(DetailedTimingMiddleware())
app.add_middleware(LoggingMiddleware(include_payloads=False))
app.add_middleware(ResponseLimitingMiddleware(max_size=1_048_576))  # 1MB
app.add_middleware(PingMiddleware())
```

### Error Handling

Catches all exceptions during tool execution and returns structured error responses. Prevents unhandled exceptions from crashing the server.

### Authentication

The `ApiClientContextMiddleware` handles:

- **STDIO mode** — forwards `API_TOKEN` to the backend API
- **HTTP mode** — optionally validates JWT tokens via JWKS
- **Identity injection** — makes authenticated user context available to tools
- **Dynamic visibility** — per-session component toggling based on scopes (opt-in)

### Timing

`DetailedTimingMiddleware` tracks execution duration for every tool call. Useful for identifying slow operations and setting up monitoring.

### Logging

`LoggingMiddleware` provides structured request/response logging for observability.

### Response Limiting

`ResponseLimitingMiddleware` provides UTF-8-safe truncation of oversized tool responses:

- Default limit: **1MB** (configurable in `fastmcp.json`)
- Prevents memory issues from unexpectedly large API responses
- Truncates cleanly at UTF-8 character boundaries

Configure in `fastmcp.json`:

```json
{
  "features": {
    "response_limiting": {
      "enabled": true,
      "max_size_bytes": 1048576
    }
  }
}
```

### Ping Middleware

`PingMiddleware` provides HTTP keepalive for long-lived connections:

- Prevents connection timeouts during long-running operations
- Essential for Streamable HTTP transport
- Automatically enabled by default

## Optional Middleware

### Response Caching

Enable with `--enable-storage --enable-caching`:

```bash
generate-mcp --enable-storage --enable-caching
```

Caches API responses with configurable TTL. Reduces backend API calls for rate-limited or expensive endpoints.

### Storage Backend

Enable with `--enable-storage`:

```bash
generate-mcp --enable-storage
```

A persistent storage backend for:

- OAuth refresh tokens
- Session state
- User preferences
- Cache persistence

## OpenTelemetry Tracing

Generated servers include optional OpenTelemetry support for distributed tracing:

```json
{
  "features": {
    "opentelemetry": {
      "enabled": true,
      "service_name": "petstore-mcp"
    }
  }
}
```

### Exporter Configuration

- **Console (default)** — spans logged to stdout
- **OTLP** — set `OTEL_EXPORTER_OTLP_ENDPOINT` for remote export

```bash
# Export to Jaeger/Tempo/etc.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python server_mcp_generated.py --transport http
```

### Installation

OpenTelemetry is an optional dependency:

```bash
pip install ".[telemetry]"
# or
uv sync --extra telemetry
```

## Customizing Middleware

The generated middleware files are meant to be customized. Edit `middleware/authentication.py` directly to add custom logic, additional validation, or domain-specific middleware.
