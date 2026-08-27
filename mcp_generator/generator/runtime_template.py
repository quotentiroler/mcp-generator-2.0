"""Server runtime tail emitted after the composition body."""

_RUNTIME_TAIL = """    try:
        print("🔧 Configuring FastMCP middleware...")
    except UnicodeEncodeError:
        print("Configuring FastMCP middleware...")
    app.add_middleware(ErrorHandlingMiddleware(include_traceback=True))
{auth_middleware_setup}
    app.add_middleware(DetailedTimingMiddleware())
    app.add_middleware(LoggingMiddleware(include_payloads=False))

    # --- FastMCP 3.1 Middleware: ResponseLimitingMiddleware ---
    _rl_cfg = _features_config.get("response_limiting", {{}})
    if _rl_cfg.get("enabled", True) and ResponseLimitingMiddleware is not None:
        _max_size = _rl_cfg.get("max_size_bytes", 1_048_576)
        app.add_middleware(ResponseLimitingMiddleware(max_size=_max_size))
        logger.info(f"  📏 ResponseLimitingMiddleware: max {{_max_size}} bytes")

    # --- FastMCP 3.0 Middleware: PingMiddleware ---
    _ping_cfg = _features_config.get("ping_middleware", {{}})
    if _ping_cfg.get("enabled", True) and PingMiddleware is not None:
        app.add_middleware(PingMiddleware())
        logger.info("  🏓 PingMiddleware: HTTP keepalive enabled")

    # --- FastMCP 3.1 Middleware: RateLimitingMiddleware ---
    _rate_limit_cfg = _features_config.get("rate_limiting", {{}})
    if _rate_limit_cfg.get("enabled", False) and RateLimitingMiddleware is not None:
        _max_rps = _rate_limit_cfg.get("max_requests_per_second", 10.0)
        _burst = _rate_limit_cfg.get("burst_capacity", int(_max_rps * 2))
        _global = _rate_limit_cfg.get("global_limit", False)
        app.add_middleware(RateLimitingMiddleware(
            max_requests_per_second=_max_rps,
            burst_capacity=_burst,
            global_limit=_global,
        ))
        logger.info(f"  🚦 RateLimitingMiddleware: {{_max_rps}} req/s, burst={{_burst}}, global={{_global}}")

    # --- OpenTelemetry tracing (FastMCP 3.0) ---
    _otel_cfg = _features_config.get("opentelemetry", {{}})
    if _otel_cfg.get("enabled", False):
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

            _service_name = _otel_cfg.get("service_name", "{api_metadata.title} MCP")
            provider = TracerProvider()
            # Default exporter: console (override via OTEL_EXPORTER_OTLP_ENDPOINT env var)
            _exporter_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            if _exporter_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_exporter_endpoint)))
                    logger.info(f"  📡 OpenTelemetry: OTLP exporter → {{_exporter_endpoint}}")
                except ImportError:
                    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
                    logger.info("  📡 OpenTelemetry: Console exporter (install opentelemetry-exporter-otlp for OTLP)")
            else:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
                logger.info("  📡 OpenTelemetry: Console exporter (set OTEL_EXPORTER_OTLP_ENDPOINT for remote)")
            trace.set_tracer_provider(provider)
            logger.info(f"  📡 OpenTelemetry tracing enabled: {{_service_name}}")
        except ImportError:
            logger.warning("  ⚠️ OpenTelemetry not available (pip install opentelemetry-api opentelemetry-sdk)")

    # --- Dynamic component visibility (FastMCP 3.0) ---
    _dv_cfg = _features_config.get("dynamic_visibility", {{}})
    if _dv_cfg.get("enabled", False):
        logger.info("  👁️ Dynamic component visibility enabled")
        logger.info("     Use ctx.enable_components() / ctx.disable_components() in auth middleware")

    try:
        print("✅ FastMCP middleware configured")
    except UnicodeEncodeError:
        print("[OK] FastMCP middleware configured")

    # Compose all servers
    _compose_mcp_servers()

    if args.transport == "stdio":
        logger.info("🚀 Starting FastMCP 3.x server with STDIO transport")
        logger.info("  🔐 Authentication: API_TOKEN environment variable")
        logger.info("  🔒 Token validation: N/A (STDIO mode - backend validates tokens)")
        logger.info(f"  📦 Modules: {module_count} composed ({{TOTAL_TOOL_COUNT}} MCP tools)")
        logger.info("  🔧 Middleware: Error handling → Auth → Timing → Logging → ResponseLimiting → Ping")
        if _transforms:
            logger.info(f"  🔄 Transforms: {{len(_transforms)}} active")
        app.run(transport="stdio")
    else:  # http
        logger.info(f"🚀 Starting FastMCP 3.x server with HTTP transport on {{args.host}}:{{args.port}}")
        logger.info("  🔐 Authentication: Bearer token in Authorization header")

        logger.info(f"  🔒 Token validation: {{'enabled (JWT)' if hasattr(args, 'validate_tokens') and args.validate_tokens else 'disabled (delegated to backend)'}}")
        logger.info(f"  📦 Modules: {module_count} composed ({{TOTAL_TOOL_COUNT}} MCP tools)")
        if _transforms:
            logger.info(f"  🔄 Transforms: {{len(_transforms)}} active")
{http_token_validation_block}


if __name__ == "__main__":
    main()
"""
