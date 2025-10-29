"""
CLI entry point for MCP generator.

Handles command-line interface, logging setup, and orchestrates the generation process.
"""

import os
import subprocess
import sys
from pathlib import Path

from .generator import generate_all, generate_main_composition_server
from .templates.authentication import generate_authentication_middleware
from .templates.event_store import generate_event_store
from .templates.oauth_provider import generate_oauth_provider
from .test_generator import generate_auth_flow_tests, generate_test_runner, generate_tool_tests
from .writers import (
    write_main_server,
    write_middleware_files,
    write_package_files,
    write_server_modules,
    write_test_files,
    write_test_runner,
)


def setup_utf8_console():
    """Configure UTF-8 encoding for console output (fixes emoji display on Windows)."""
    if sys.platform == "win32":
        # Set console to UTF-8 mode on Windows
        os.system("chcp 65001 > nul 2>&1")
        # Reconfigure stdout encoding if available (Python 3.7+)
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass  # Not available or failed, continue anyway


def print_metadata_summary(api_metadata, security_config):
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

    print("\n🔐 Security Configuration:")
    if security_config.schemes:
        print(f"   Authentication: {', '.join(security_config.schemes.keys())}")
    if security_config.default_scopes:
        print(f"   Default scopes: {', '.join(security_config.default_scopes)}")
    if security_config.oauth_config:
        oauth = security_config.oauth_config
        print(f"   OAuth2 flows: {', '.join(oauth.flows.keys())}")
        print(f"   Available scopes: {len(oauth.all_scopes)}")


def main():
    """Main CLI entry point."""
    import argparse

    setup_utf8_console()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MCP Generator 2.0 - OpenAPI to FastMCP 2.0 Server Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use local openapi.json (default)
  generate-mcp

  # Specify custom file
  generate-mcp --file ./my-api-spec.yaml

  # Download from URL
  generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

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

    args = parser.parse_args()

    print("=" * 80)
    print("MCP Generator 2.0 - OpenAPI to FastMCP 2.0 Server Generator")
    print("=" * 80)

    # Use current working directory for all operations
    src_dir = Path.cwd()
    # For scripts and templates, use the package location
    package_dir = Path(__file__).parent.parent

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

    # Ensure API client exists before trying to introspect it
    generated_dir = src_dir / "generated_openapi"
    openapi_client_dir = generated_dir / "openapi_client"

    if not (openapi_client_dir.exists() and (openapi_client_dir / "__init__.py").exists()):
        print("\n🔨 Generating Python API client from OpenAPI specification...")
        print("   This is a one-time step that may take a few moments.")

        # Try to find the script in multiple locations
        # 1. Development: repo_root/scripts/generate_openapi_client.py
        # 2. Installed: site-packages/scripts/generate_openapi_client.py
        script_locations = [
            package_dir / "scripts" / "generate_openapi_client.py",  # Both dev and installed
        ]

        script_path = None
        for location in script_locations:
            if location.exists():
                script_path = location
                break

        if not script_path:
            print("\n❌ API Client Generator Not Found")
            print("\nSearched in:")
            for loc in script_locations:
                print(f"   - {loc}")
            print("\n💡 The scripts package may not be installed correctly.")
            print("   Please reinstall mcp-generator:")
            print("   pip install --force-reinstall mcp-generator")
            print("   OR")
            print("   uv pip install --reinstall mcp-generator")
            sys.exit(1)

        print(f"   Running: python {script_path.name}")
        try:
            import platform

            is_windows = platform.system() == "Windows"

            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # Replace invalid characters instead of crashing
                check=False,
                shell=is_windows,
                cwd=str(src_dir),
            )

            if result.returncode != 0:
                print("\n❌ API Client Generation Failed")
                print(
                    "\nThe OpenAPI Generator encountered an error while generating the Python client."
                )
                print("\n📋 Error details:")
                if result.stdout:
                    print(f"STDOUT: {result.stdout[:500]}")
                if result.stderr:
                    print(f"STDERR: {result.stderr[:500]}")
                print("\n💡 To fix this:")
                print("   1. Verify your openapi.json is valid:")
                print("      python scripts/validate_openapi.py")
                print("   2. Check that OpenAPI Generator is installed:")
                print("      npx @openapitools/openapi-generator-cli version")
                print("   3. Try generating manually:")
                print("      python scripts/generate_openapi_client.py")
                print()
                sys.exit(1)

            print("   ✅ API client generated successfully")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\n💡 Please generate the API client manually:")
            print("   python scripts/generate_openapi_client.py")
            print()
            sys.exit(1)

    try:
        # Generate all components
        print("\n🏗️  Analyzing API structure...")
        api_metadata, security_config, modules, total_tools = generate_all(src_dir)

        # Print summary
        print_metadata_summary(api_metadata, security_config)

        # Determine output paths (use current working directory)
        output_dir = src_dir / "generated_mcp"
        servers_dir = output_dir / "servers"
        middleware_dir = output_dir / "middleware"

        # Write server modules
        print(f"\n📦 Generating {len(modules)} server modules...")
        write_server_modules(modules, servers_dir)

        # Generate and write middleware (only if authentication is configured)
        if security_config.has_authentication():
            print("\n🔐 Generating authentication middleware...")
            middleware_code = generate_authentication_middleware(api_metadata, security_config)
            oauth_code = generate_oauth_provider(api_metadata, security_config)
            event_store_code = generate_event_store()
            write_middleware_files(middleware_code, oauth_code, event_store_code, middleware_dir)
        else:
            print("\n🔓 No authentication configured - skipping middleware generation")

        # Generate and write main composition server
        print("\n🔗 Generating main composition server...")
        main_server_code = generate_main_composition_server(modules, api_metadata, security_config)
        # Use API title for filename (sanitized - replace spaces, hyphens, AND dots)
        # Also remove version patterns like "1.0", "v2.0", "3.0" from the name
        import re

        clean_title = re.sub(r"\s+v?\d+\.\d+(\.\d+)?", "", api_metadata.title, flags=re.IGNORECASE)
        server_name = clean_title.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        # Remove multiple consecutive underscores
        server_name = re.sub(r"_+", "_", server_name).strip("_")
        main_output_file = output_dir / f"{server_name}_mcp_generated.py"
        write_main_server(main_server_code, main_output_file)

        # Generate package files (README, pyproject.toml, __init__.py)
        print("\n📦 Generating package metadata files...")
        write_package_files(output_dir, api_metadata, security_config, modules, total_tools)

        # Generate test files (conditionally include auth tests)
        if security_config.has_authentication():
            print("\n🧪 Generating authentication flow demonstration tests...")
            test_dir = src_dir / "test" / "generated"
            auth_test_code = generate_auth_flow_tests(api_metadata, security_config, modules)
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(auth_test_code, tool_test_code, test_dir)
        else:
            print("\n🧪 Generating basic tool tests (no auth required)...")
            test_dir = src_dir / "test" / "generated"
            # Generate simplified tests without auth requirements
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(None, tool_test_code, test_dir)

        # Generate test runner script
        print("\n🏃 Generating test runner...")
        test_runner_code = generate_test_runner(api_metadata, server_name)
        write_test_runner(test_runner_code, src_dir / "test" / "run_tests.py")

        # Print success summary
        print("\n" + "=" * 80)
        print("✅ Generation Complete!")
        print("=" * 80)
        print("\n� Summary:")
        print(f"   • Generated {total_tools} MCP tools across {len(modules)} modules")
        if security_config.has_authentication():
            print("   • Created authentication middleware with JWT validation")
            print("   • Generated OAuth2 provider for backend integration")
            print("   • Created comprehensive test suites with automated test runner")
        else:
            print("   • No authentication required (public API)")
            print("   • Created basic test suite with automated test runner")

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
        print("     export BACKEND_API_TOKEN=your_token")
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
        print()

    except ModuleNotFoundError as e:
        print("\n❌ Module Import Error")
        print(f"\nCould not import required module: {e}")
        print("\n💡 This usually means:")
        print("   1. The API client generation was incomplete")
        print("   2. A required dependency is missing")
        print("\n🔧 To resolve:")
        print("   • Regenerate the API client:")
        print("     python scripts/generate_openapi_client.py")
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
        print("   • Validate your OpenAPI spec: python scripts/validate_openapi.py")
        print("   • Report issues: https://github.com/quotentiroler/mcp-generator-2.0/issues")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
