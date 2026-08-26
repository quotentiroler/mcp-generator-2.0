"""
CLI entry point for MCP generator.

Handles command-line interface, logging setup, and orchestrates the generation process.
"""

import os
import sys
from pathlib import Path
from typing import Any

from .config import DEFAULT_FASTMCP_TARGET
from .fastmcp_target import SUPPORTED_TARGETS, resolve_target
from .generator import generate_all, generate_main_composition_server
from .templates.authentication import generate_authentication_middleware
from .templates.cache_middleware import generate_cache_middleware
from .templates.event_store import generate_event_store
from .templates.oauth_provider import generate_oauth_provider
from .templates.storage_backend import generate_storage_backend
from .test_generator import (
    generate_auth_flow_tests,
    generate_behavioral_tests,
    generate_cache_tests,
    generate_http_basic_tests,
    generate_multi_auth_tests,
    generate_oauth_persistence_tests,
    generate_openapi_feature_tests,
    generate_performance_tests,
    generate_resource_tests,
    generate_server_integration_tests,
    generate_test_runner,
    generate_tool_call_tests,
    generate_tool_schema_tests,
    generate_tool_tests,
    generate_transform_tests,
)
from .writers import (
    write_main_server,
    write_middleware_files,
    write_package_files,
    write_server_modules,
    write_test_files,
    write_test_runner,
)


def setup_utf8_console() -> None:
    """Configure UTF-8 encoding for console output (fixes emoji display on Windows)."""
    if sys.platform == "win32":
        # Set console to UTF-8 mode on Windows
        os.system("chcp 65001 > nul 2>&1")
        # Reconfigure stdout encoding if available (Python 3.7+)
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass  # Not available or failed, continue anyway


def print_metadata_summary(api_metadata: Any, security_config: Any) -> None:
    """Print API metadata and security configuration summary."""
    print("\n📋 API Metadata:")
    print(f"   Title: {api_metadata.title}")
    print(f"   Version: {api_metadata.version}")
    if api_metadata.description:
        print(f"   Description: {api_metadata.description[:80]}...")
    if api_metadata.contact and api_metadata.contact.get("email"):
        print(f"   Contact: {api_metadata.contact['email']}")
    if api_metadata.license and api_metadata.license.get("name"):
        print(f"   License: {api_metadata.license['name']}")
    if api_metadata.servers:
        print(f"   Servers: {len(api_metadata.servers)} configured")
    if api_metadata.tags:
        print(f"   Tags: {len(api_metadata.tags)} categories")

    backend_url = api_metadata.backend_url
    print(f"   Backend URL: {backend_url}")
    if api_metadata.has_relative_server_url:
        print(f"\n   ⚠️  WARNING: Server URL '{backend_url}' is relative (no host).")
        print("   The generated code will not work without setting API_BASE_URL at runtime.")
        print("   Set it via environment variable or in your MCP client config, e.g.:")
        print("   API_BASE_URL=https://your-api-host.com/api/v3")

    print("\n🔐 Security Configuration:")
    if security_config.schemes:
        print(f"   Authentication: {', '.join(security_config.schemes.keys())}")
    if security_config.default_scopes:
        print(f"   Default scopes: {', '.join(security_config.default_scopes)}")
    if security_config.oauth_config:
        oauth = security_config.oauth_config
        print(f"   OAuth2 flows: {', '.join(oauth.flows.keys())}")
        print(f"   Available scopes: {len(oauth.all_scopes)}")


def main() -> None:
    """Main CLI entry point."""
    import argparse

    setup_utf8_console()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MCP Generator 3.x - OpenAPI to FastMCP 3.x Server Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation (minimal server)
  generate-mcp

  # With custom OpenAPI file
  generate-mcp --file ./my-api-spec.yaml

  # Download from URL
  generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

  # With optional features
  generate-mcp --enable-storage --enable-caching
  generate-mcp --enable-resources
  generate-mcp --enable-apps
  generate-mcp --enable-apps --generate-ui

  # Enrich descriptions with an overlay or auto-enhance
  generate-mcp --overlay ./my-overlay.yaml
  generate-mcp --overlay fhir --schema-depth 5
  generate-mcp --auto-overlay

  # Generate A2A agent adapter
  generate-mcp --enable-a2a

Optional Features (disabled by default for simplicity):
  --enable-storage    Persistent storage for OAuth tokens & state
  --enable-caching    Response caching (reduces API calls)
  --enable-resources  MCP resources from GET endpoints
  --enable-apps       MCP Apps with interactive UI display tools
  --generate-ui       API-specific display tools from response schemas (requires --enable-apps)
  --overlay FILE      Apply OpenAPI Overlay 1.0.0 to enrich descriptions
  --auto-overlay      Auto-generate rule-based overlay for AI-friendly descriptions
  --enable-a2a        Generate A2A agent adapter + AgentCard

Documentation: https://github.com/quotentiroler/mcp-generator-2.0
        """,
    )

    parser.add_argument(
        "--file",
        type=str,
        default="./openapi.json",
        help="Path to OpenAPI specification file (default: ./openapi.json)",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL to download OpenAPI specification from (overrides --file)",
    )

    parser.add_argument(
        "--enable-storage",
        action="store_true",
        default=False,
        help="Enable persistent storage backend (for OAuth tokens, session state, user data)",
    )

    parser.add_argument(
        "--enable-caching",
        action="store_true",
        default=False,
        help="Enable response caching middleware (reduces backend API calls, requires --enable-storage)",
    )

    parser.add_argument(
        "--enable-resources",
        action="store_true",
        default=False,
        help="Generate MCP resource templates from GET endpoints (exposes API data as resources)",
    )

    parser.add_argument(
        "--enable-apps",
        action="store_true",
        default=False,
        help="Generate MCP Apps display tools (interactive tables, charts, forms) and optional GenerativeUI",
    )

    parser.add_argument(
        "--generate-ui",
        action="store_true",
        default=False,
        help="Generate API-specific display tools from OpenAPI response schemas (requires --enable-apps)",
    )

    parser.add_argument(
        "--schema-depth",
        type=int,
        default=3,
        help="Max nesting depth for response schema parsing (default: 3, increase for deeply nested APIs)",
    )

    parser.add_argument(
        "--overlay",
        type=str,
        default=None,
        help="Overlay name or path. Bundled: 'fhir'. Or a path to an Overlay 1.0.0 file",
    )

    parser.add_argument(
        "--auto-overlay",
        action="store_true",
        default=False,
        help="Auto-generate a rule-based overlay to enhance API descriptions for AI agents",
    )

    parser.add_argument(
        "--enable-a2a",
        action="store_true",
        default=False,
        help="Generate A2A (Agent-to-Agent) adapter and AgentCard for multi-agent orchestration",
    )

    parser.add_argument(
        "--fastmcp-target",
        type=int,
        choices=SUPPORTED_TARGETS,
        default=DEFAULT_FASTMCP_TARGET,
        help=(
            "FastMCP major version the generated server targets "
            f"(default: {DEFAULT_FASTMCP_TARGET}). 4 is a prerelease target: it drops "
            "server-side sampling and replaces elicitation with a guard response, "
            "which the sessionless 2026-07-28 protocol requires"
        ),
    )

    args = parser.parse_args()
    target = resolve_target(args.fastmcp_target)
    if target.is_prerelease:
        print(
            f"⚠️  Targeting FastMCP {target.major}.x (prerelease: "
            f"{target.dependency_pin()}) — pin exactly and expect sharp edges."
        )

    print("=" * 80)
    print("MCP Generator 3.x - OpenAPI to FastMCP 3.x Server Generator")
    print("=" * 80)

    # Use current working directory for all operations
    src_dir = Path.cwd()

    # Handle URL download if specified
    if args.url:
        print("\n📥 Downloading OpenAPI specification from URL...")
        print(f"   {args.url}")

        try:
            import httpx

            response = httpx.get(args.url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            # Preserve file extension based on URL
            if args.url.endswith(".yaml") or args.url.endswith(".yml"):
                openapi_spec = src_dir / "openapi.yaml"
            else:
                openapi_spec = src_dir / "openapi.json"

            openapi_spec.write_bytes(response.content)
            print(f"   ✅ Downloaded to: {openapi_spec.name}")

        except Exception as e:
            print("\n❌ Failed to download OpenAPI specification")
            print(f"\n   Error: {e}")
            print("\n💡 To fix this:")
            print("   • Check the URL is accessible")
            print("   • Try downloading manually and use --file instead")
            print()
            sys.exit(1)
    else:
        # Use file path (absolute or relative to current directory)
        file_path = Path(args.file)
        if file_path.is_absolute():
            openapi_spec = file_path
        else:
            openapi_spec = src_dir / args.file

    # Check for OpenAPI spec
    if not openapi_spec.exists():
        print("\n❌ OpenAPI Specification Not Found")
        print("\nThe generator requires an OpenAPI specification file to proceed.")
        print("\n📋 Expected location:")
        print(f"   {openapi_spec}")
        print("\n💡 To get started:")
        print("   1. Place your openapi.json file in the project root")
        print("   2. Or specify a custom file:")
        print("      generate-mcp --file ./path/to/spec.yaml")
        print("   3. Or download from URL:")
        print("      generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json")
        print("\n📚 Documentation: https://github.com/quotentiroler/mcp-generator-2.0")
        print()
        sys.exit(1)

    print(f"\n✅ Found OpenAPI specification: {openapi_spec.name}")

    # --- Apply OpenAPI Overlay if requested ---
    if args.overlay or args.auto_overlay:
        import copy
        import json as _json_overlay

        from .introspection import _load_openapi_spec
        from .overlay import apply_overlay, generate_overlay, load_overlay, resolve_overlay_path

        raw_spec = _load_openapi_spec(openapi_spec)
        if raw_spec is None:
            print("\n❌ Could not load OpenAPI spec for overlay processing")
            sys.exit(1)

        spec_copy = copy.deepcopy(raw_spec)

        if args.overlay:
            overlay_path = resolve_overlay_path(args.overlay)
            print(f"\n📝 Applying OpenAPI Overlay: {overlay_path}")
            overlay_doc = load_overlay(overlay_path)
            apply_overlay(spec_copy, overlay_doc)
            action_count = len(overlay_doc.get("actions", []))
            print(f"   ✅ Applied {action_count} overlay actions")

        if args.auto_overlay:
            print("\n🤖 Auto-generating rule-based overlay for AI-friendly descriptions...")
            auto_overlay = generate_overlay(spec_copy)
            apply_overlay(spec_copy, auto_overlay)
            print(f"   ✅ Enhanced {len(auto_overlay.get('actions', []))} descriptions")

        # Write the enhanced spec back (to a separate file to preserve the original)
        enhanced_spec_path = (
            openapi_spec.parent / f"{openapi_spec.stem}_enhanced{openapi_spec.suffix}"
        )
        with open(enhanced_spec_path, "w", encoding="utf-8") as _f:
            _json_overlay.dump(spec_copy, _f, indent=2)
        openapi_spec = enhanced_spec_path
        print(f"   📄 Enhanced spec: {enhanced_spec_path.name}")

    # Always (re-)generate the API client so method bodies stay in sync
    # with the current openapi-py-fetch runtime.
    generated_dir = src_dir / "generated_openapi"
    _openapi_client_dir = generated_dir / "openapi_client"

    print("\n🔨 Generating Python API client from OpenAPI specification...")

    try:
        import json as _json

        with open(openapi_spec, encoding="utf-8") as _f:
            openapi_spec_dict = _json.load(_f)

        from openapi_py_fetch.generator import generate_client_package

        from .introspection import enrich_spec_tags

        generated_dir.mkdir(parents=True, exist_ok=True)
        ok = generate_client_package(
            openapi_spec_dict, generated_dir, enrich_tags_fn=enrich_spec_tags
        )
        if not ok:
            print("\n❌ API Client Generation Failed")
            print("\n💡 Verify your openapi.json is valid:")
            print("      python -m mcp_generator.scripts.validate_openapi")
            sys.exit(1)

        print("   ✅ API client generated successfully")
    except Exception as e:
        print(f"\n❌ Error generating API client: {e}")
        print("\n💡 Verify your openapi.json is valid:")
        print("      python -m mcp_generator.scripts.validate_openapi")
        sys.exit(1)

    try:
        # Generate all components
        print("\n🏗️  Analyzing API structure...")
        api_metadata, security_config, modules, total_tools = generate_all(
            src_dir, enable_resources=args.enable_resources, target=target
        )

        # Calculate resource count early for conditional logic
        total_resources = sum(mod.resource_count for mod in modules.values())

        # Print summary
        print_metadata_summary(api_metadata, security_config)

        # Determine output paths (use current working directory)
        output_dir = src_dir / "generated_mcp"
        servers_dir = output_dir / "servers"
        middleware_dir = output_dir / "middleware"

        # Write server modules
        print(f"\n📦 Generating {len(modules)} server modules...")
        write_server_modules(modules, servers_dir)

        # Generate and write middleware (ALWAYS needed even without auth for openapi_client setup)
        print("\n🔐 Generating API client middleware...")
        middleware_code = generate_authentication_middleware(
            api_metadata, security_config, target=target
        )
        oauth_code = generate_oauth_provider(api_metadata, security_config, target=target)
        event_store_code = generate_event_store()
        write_middleware_files(middleware_code, oauth_code, event_store_code, middleware_dir)

        if not security_config.has_authentication():
            print("   💡 Note: Middleware provides unauthenticated API client for backend calls")

        # Generate storage backend if requested
        if args.enable_storage:
            print("\n💾 Generating pluggable storage backend...")
            storage_code = generate_storage_backend()
            storage_file = output_dir / "storage.py"
            storage_file.write_text(storage_code, encoding="utf-8")
            print("   ✅ storage.py")
            if security_config.has_authentication():
                print("   💡 OAuth tokens will persist across server restarts")
            print("   💡 Use for caching, session state, or custom data")

        # Generate cache middleware if requested
        if args.enable_caching:
            if not args.enable_storage:
                print("\n⚠️  Warning: --enable-caching requires --enable-storage")
                print("   Skipping cache generation. Please re-run with both flags.")
            else:
                print("\n⚡ Generating response caching middleware...")
                cache_code = generate_cache_middleware()
                cache_file = output_dir / "cache.py"
                cache_file.write_text(cache_code, encoding="utf-8")
                print("   ✅ cache.py")
                print("   💡 Decorate expensive tools with @cache.cached(ttl=600)")

        # Generate MCP Apps display tools if requested
        if args.enable_apps:
            print("\n🎨 Generating MCP Apps display tools...")
            from .writers import write_apps_package

            write_apps_package(output_dir)

        # Generate API-specific display tools from response schemas
        display_module_count = 0
        if args.generate_ui:
            if not args.enable_apps:
                print("\n⚠️  Warning: --generate-ui requires --enable-apps")
                print("   Skipping API-specific display tool generation.")
            else:
                print("\n🖼️  Generating API-specific display tools from response schemas...")
                from .display_renderers import render_display_module
                from .introspection import (
                    get_delete_endpoints,
                    get_display_endpoints,
                    get_form_endpoints,
                )
                from .writers import write_display_modules

                display_endpoints = get_display_endpoints(
                    src_dir, max_depth=args.schema_depth, spec=openapi_spec_dict
                )
                form_endpoints = get_form_endpoints(
                    src_dir, max_depth=args.schema_depth, spec=openapi_spec_dict
                )
                delete_endpoints = get_delete_endpoints(src_dir, spec=openapi_spec_dict)
                display_modules = {}
                for tag, endpoints in display_endpoints.items():
                    api_var = f"{tag}_api"
                    api_class_name = tag.title().replace("_", "") + "Api"
                    tag_forms = form_endpoints.get(tag, [])
                    tag_deletes = delete_endpoints.get(tag, [])
                    code = render_display_module(
                        tag,
                        endpoints,
                        api_var,
                        api_class_name,
                        form_endpoints=tag_forms,
                        delete_endpoints=tag_deletes,
                    )
                    if code:
                        display_modules[tag] = code
                        display_module_count = len(display_modules)

                # Also generate modules for tags with forms/deletes but no display endpoints
                all_tags = set(form_endpoints.keys()) | set(delete_endpoints.keys())
                for tag in all_tags:
                    if tag not in display_modules:
                        forms = form_endpoints.get(tag, [])
                        deletes = delete_endpoints.get(tag, [])
                        if not forms and not deletes:
                            continue
                        api_var = f"{tag}_api"
                        api_class_name = tag.title().replace("_", "") + "Api"
                        code = render_display_module(
                            tag,
                            [],
                            api_var,
                            api_class_name,
                            form_endpoints=forms,
                            delete_endpoints=deletes,
                        )
                        if code:
                            display_modules[tag] = code
                            display_module_count = len(display_modules)

                if display_modules:
                    write_display_modules(display_modules, output_dir / "apps")
                else:
                    print("   ℹ️  No API endpoints with parseable response schemas found.")

        # Generate A2A (Agent-to-Agent) adapter if requested
        if args.enable_a2a:
            print("\n🤖 Generating A2A agent adapter and AgentCard...")
            from .a2a import generate_agent_card, render_a2a_adapter

            agent_card = generate_agent_card(api_metadata, modules)
            agent_card_path = output_dir / "agent_card.json"
            import json as _a2a_json

            agent_card_path.write_text(_a2a_json.dumps(agent_card, indent=2), encoding="utf-8")
            print(f"   ✅ agent_card.json ({len(agent_card['skills'])} skills)")

            adapter_code = render_a2a_adapter(api_metadata)
            adapter_path = output_dir / "a2a_adapter.py"
            adapter_path.write_text(adapter_code, encoding="utf-8")
            print("   ✅ a2a_adapter.py")
            print("   💡 Install A2A deps: pip install a2a-sdk starlette uvicorn")

        # Generate and write main composition server
        print("\n🔗 Generating main composition server...")

        # Load composition configuration from fastmcp.json if it exists
        composition_strategy = "mount"  # default (FastMCP 3.x uses mount with namespace)
        fastmcp_json_path = output_dir / "fastmcp.json"
        if fastmcp_json_path.exists():
            try:
                import json

                with open(fastmcp_json_path, encoding="utf-8") as f:
                    config = json.load(f)
                    composition_config = config.get("composition", {})
                    composition_strategy = composition_config.get("strategy", "mount")
            except Exception as e:
                print(f"⚠️  Could not load composition config from fastmcp.json: {e}")

        main_server_code = generate_main_composition_server(
            modules,
            api_metadata,
            security_config,
            composition_strategy=composition_strategy,
            enable_apps=args.enable_apps,
            display_tags=list(display_modules.keys())
            if args.generate_ui and args.enable_apps and display_module_count > 0
            else None,
            target=target,
        )
        from .utils import sanitize_server_name

        server_name = sanitize_server_name(api_metadata.title)
        main_output_file = output_dir / f"{server_name}_mcp_generated.py"
        write_main_server(main_server_code, main_output_file)

        # Generate package files (README, pyproject.toml, __init__.py)
        print("\n📦 Generating package metadata files...")
        write_package_files(
            output_dir,
            api_metadata,
            security_config,
            modules,
            total_tools,
            args.enable_storage,
            args.enable_apps,
            target=target,
        )

        # Generate test files (conditionally include auth tests)
        print("\n🧪 Generating test suites...")
        test_dir = src_dir / "test" / "generated"

        # Generate all test suites
        print("   • OpenAPI feature tests")
        openapi_feature_test_code = generate_openapi_feature_tests(
            api_metadata, security_config, modules
        )
        print("   • HTTP basic E2E tests")
        http_basic_test_code = generate_http_basic_tests(api_metadata, security_config, modules)
        print("   • Performance tests")
        performance_test_code = generate_performance_tests(api_metadata, security_config, modules)

        # Generate cache tests if caching is enabled
        cache_test_code = None
        if args.enable_caching:
            print("   • Cache middleware tests")
            cache_test_code = generate_cache_tests()

        # Generate OAuth persistence tests if storage is enabled with authentication
        oauth_persistence_test_code = None
        if args.enable_storage and security_config.has_authentication():
            print("   • OAuth token persistence tests")
            oauth_persistence_test_code = generate_oauth_persistence_tests()

        # Generate resource tests if resources are enabled
        resource_test_code = None
        if args.enable_resources and total_resources > 0:
            print("   • Resource template tests")
            resource_test_code = generate_resource_tests(modules, api_metadata, security_config)

        # Always generate transform tests (FastMCP 3.x features)
        print("   • FastMCP 3.x transform tests")
        transform_test_code = generate_transform_tests(api_metadata, security_config, modules)

        # Generate multi-auth tests if auth is configured
        multi_auth_test_code = None
        if security_config.has_authentication():
            print("   • FastMCP 3.x multi-auth tests")
            multi_auth_test_code = generate_multi_auth_tests(api_metadata, security_config, modules)

        # Always generate in-process integration tests and schema validation
        print("   • Server integration tests (in-process)")
        server_integration_test_code = generate_server_integration_tests(
            modules, api_metadata, security_config
        )
        print("   • Tool schema validation tests")
        tool_schema_test_code = generate_tool_schema_tests(modules, api_metadata, security_config)
        print("   • Behavioral edge-case tests (failure-driven)")
        behavioral_test_code = generate_behavioral_tests(modules, api_metadata, security_config)

        # Generate real tools/call E2E tests (always)
        print("   • Tool call E2E tests (tools/call)")
        tool_call_test_code = generate_tool_call_tests(modules, api_metadata, security_config)

        if security_config.has_authentication():
            print("   • Authentication flow tests")
            auth_test_code = generate_auth_flow_tests(api_metadata, security_config, modules)
            print("   • Tool validation tests")
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(
                auth_test_code,
                tool_test_code,
                openapi_feature_test_code,
                http_basic_test_code,
                performance_test_code,
                cache_test_code,
                oauth_persistence_test_code,
                test_dir,
                resource_test_code,
                transform_test_code,
                multi_auth_test_code,
                server_integration_test_code,
                tool_schema_test_code,
                behavioral_test_code,
                tool_call_test_code,
            )
        else:
            print("   • Basic tool tests (no auth required)")
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(
                None,
                tool_test_code,
                openapi_feature_test_code,
                http_basic_test_code,
                performance_test_code,
                cache_test_code,
                oauth_persistence_test_code,
                test_dir,
                resource_test_code,
                transform_test_code,
                multi_auth_test_code,
                server_integration_test_code,
                tool_schema_test_code,
                behavioral_test_code,
                tool_call_test_code,
            )

        # Generate test runner script
        print("\n🏃 Generating test runner...")
        test_runner_code = generate_test_runner(api_metadata, server_name)
        write_test_runner(test_runner_code, src_dir / "test" / "run_tests.py")

        # Print success summary
        total_resources = sum(spec.resource_count for spec in modules.values())

        print("\n" + "=" * 80)
        print("✅ Generation Complete!")
        print("=" * 80)
        print("\n📊 Summary:")
        print(f"   • Generated {total_tools} MCP tools across {len(modules)} modules")
        if args.enable_resources and total_resources > 0:
            print(f"   • Generated {total_resources} MCP resource templates (RFC 6570 URIs)")
        if security_config.has_authentication():
            print("   • Created authentication middleware with JWT validation")
            print("   • Generated OAuth2 provider for backend integration")
            print("   • Created comprehensive test suites with automated test runner")
        else:
            print("   • No authentication required (public API)")
            print("   • Created basic test suite with automated test runner")

        # Show enabled optional features
        if args.enable_storage:
            print("   • Enabled: Persistent storage backend (storage.py, cache_middleware.py)")
        if args.enable_caching:
            print("   • Enabled: Response caching with configurable TTL")
        if args.enable_resources and total_resources > 0:
            print("   • Enabled: MCP resources for data access")
        if args.enable_apps:
            print(
                "   • Enabled: MCP Apps display tools (show_table, show_detail, show_chart, show_form, show_comparison)"
            )
            if args.generate_ui and display_module_count > 0:
                print(
                    f"   • Enabled: {display_module_count} API-specific display modules (tables, detail cards)"
                )
            print("   💡 Install UI deps: pip install 'fastmcp[apps]'")
        if args.enable_a2a:
            print("   • Enabled: A2A agent adapter + AgentCard (agent_card.json, a2a_adapter.py)")
        if args.overlay or args.auto_overlay:
            print("   • Applied: OpenAPI Overlay description enrichment")

        print("\n📂 Output Location:")
        print(f"   {output_dir.relative_to(src_dir)}/")

        print("\n🧪 Run Tests:")
        print("   python test/run_tests.py")
        print("   (automatically starts server, runs tests, and cleans up)")

        print("\n🚀 Next Steps:")
        print("   1. Review generated server:")
        print(f"      cat {main_output_file.relative_to(src_dir)}")
        if security_config.has_authentication():
            print("   2. Configure authentication (see generated README.md)")
            print("   3. Run your MCP server:")
        else:
            print("   2. Run your MCP server:")
        print(f"      python {main_output_file.relative_to(src_dir)}")

        print("\n� Usage Modes:")
        print("   • STDIO: For Claude Desktop, Cline, etc.")
        print("     export API_TOKEN=your_token")
        print(f"     python {server_name}_mcp_generated.py")
        print("\n   • HTTP: For web-based MCP clients")
        print(f"     python {server_name}_mcp_generated.py --transport=http --port=8000")
        print("\n   • HTTP with JWT validation:")
        print(
            f"     python {server_name}_mcp_generated.py --transport=http --port=8000 --validate-tokens"
        )

        print("\n📚 Documentation:")
        print(f"   • README: {output_dir.relative_to(src_dir)}/README.md")
        print("   • Tests: test/generated/")
        print("   • Test Runner: test/run_tests.py")
        print("   • GitHub: https://github.com/quotentiroler/mcp-generator-2.0")

        # Show optional features that were not enabled
        disabled_features = []
        if not args.enable_storage:
            disabled_features.append(
                ("--enable-storage", "Persistent OAuth tokens & state across restarts")
            )
        if not args.enable_caching:
            disabled_features.append(
                ("--enable-caching", "Cache API responses (reduces rate limit impact)")
            )
        if not args.enable_resources:
            disabled_features.append(("--enable-resources", "Expose API data as MCP resources"))
        if not args.enable_apps:
            disabled_features.append(
                ("--enable-apps", "Interactive UI display tools (tables, charts, forms)")
            )

        if disabled_features:
            print("\n💡 Optional Features (not enabled):")
            for flag, description in disabled_features:
                print(f"   {flag:20s} → {description}")

            # Build regeneration command
            flags_str = " ".join([flag for flag, _ in disabled_features])
            if args.url:
                print(f"\n   To enable: generate-mcp --url {args.url} {flags_str}")
            elif args.file != "./openapi.json":
                print(f"\n   To enable: generate-mcp --file {args.file} {flags_str}")
            else:
                print(f"\n   To enable: generate-mcp {flags_str}")

        print()

    except ModuleNotFoundError as e:
        print("\n❌ Module Import Error")
        print(f"\nCould not import required module: {e}")
        print("\n💡 This usually means:")
        print("   1. The API client generation was incomplete")
        print("   2. A required dependency is missing")
        print("\n🔧 To resolve:")
        print("   • Regenerate the API client:")
        print("     python -m mcp_generator.scripts.generate_openapi_client")
        print("   • Check dependencies:")
        print("     uv sync")
        print()
        sys.exit(1)

    except Exception as e:
        print("\n❌ Generation Error")
        print(f"\nAn unexpected error occurred: {str(e)}")
        print("\n📋 Stack trace:")
        import traceback

        traceback.print_exc()
        print("\n💡 For help:")
        print("   • Check the error message above")
        print("   • Validate your OpenAPI spec: python -m mcp_generator.scripts.validate_openapi")
        print("   • Report issues: https://github.com/quotentiroler/mcp-generator-2.0/issues")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
