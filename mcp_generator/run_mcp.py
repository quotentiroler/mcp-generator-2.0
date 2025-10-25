"""
Global run-mcp CLI command.

This is a dispatcher that can run any registered MCP server by name.
Servers are registered via the local registry file at ~/.mcp-generator/servers.json
Use 'register-mcp' to add servers to the registry.
"""

import argparse
import json
import sys
from pathlib import Path


def get_registry_path() -> Path:
    """Get the path to the local MCP servers registry."""
    return Path.home() / ".mcp-generator" / "servers.json"


def load_local_registry() -> dict:
    """Load the local MCP servers registry."""
    registry_path = get_registry_path()
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def list_servers():
    """List all registered MCP servers from local registry."""
    return load_local_registry()


def main():
    """Main entry point for run-mcp CLI."""
    parser = argparse.ArgumentParser(
        description="Run a registered MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "server_name",
        nargs="?",
        help="Name of the MCP server to run (use --list to see available servers)",
    )
    parser.add_argument("--list", action="store_true", help="List all registered MCP servers")
    parser.add_argument(
        "--mode",
        "--transport",
        dest="transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to for HTTP transport (default: 8000)"
    )
    parser.add_argument(
        "--validate-tokens",
        action="store_true",
        help="Enable JWT token validation for HTTP transport",
    )

    args = parser.parse_args()

    # Get registered servers
    servers = list_servers()

    # Handle --list flag
    if args.list:
        if not servers:
            print("No MCP servers registered.")
            print(f"\nRegistry location: {get_registry_path()}")
            print("\nTo register a server:")
            print("  uv run register-mcp /path/to/server")
            return 0

        print("Registered MCP Servers:")
        print("=" * 70)
        for name, info in sorted(servers.items()):
            print(f"\n  • {name}")
            print(f"    Path: {info['path']}")
            print(f"    Entry point: {info['entry_point']}")
            if info.get("description"):
                print(f"    Description: {info['description']}")
        print(f"\n{'=' * 70}")
        print(f"Registry location: {get_registry_path()}")
        print("\nUsage: uv run run-mcp <server_name> [options]")
        return 0

    # Require server name if not listing
    if not args.server_name:
        parser.error("server_name is required (use --list to see available servers)")

    # Check if server exists
    if args.server_name not in servers:
        print(f"❌ Error: Server '{args.server_name}' not found.")
        print("\nAvailable servers:")
        if servers:
            for name in sorted(servers.keys()):
                print(f"  • {name}")
        else:
            print("  (none registered)")
        print("\nUsage: uv run run-mcp <server_name> [options]")
        print("       uv run run-mcp --list")
        print("       uv run register-mcp /path/to/server")
        return 1

    # Load and run the server
    try:
        print(f"🚀 Loading MCP server: {args.server_name}")
        info = servers[args.server_name]
        server_path = Path(info["path"])
        entry_point = info["entry_point"]  # e.g. "module_name:main"

        # Add server path to sys.path
        if str(server_path) not in sys.path:
            sys.path.insert(0, str(server_path))

        # Import and get the main function
        module_name, func_name = entry_point.split(":")
        module = __import__(module_name)
        server_main = getattr(module, func_name)

        # Set up sys.argv for the server's argument parser
        sys.argv = ["run-mcp", "--transport", args.transport]

        if args.transport == "http":
            sys.argv.extend(["--host", args.host, "--port", str(args.port)])
            if args.validate_tokens:
                sys.argv.append("--validate-tokens")

        # Run the server's main function
        server_main()

    except Exception as e:
        print(f"❌ Error loading/running server '{args.server_name}': {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
