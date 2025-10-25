"""
Global register-mcp CLI command.

Registers local MCP servers so they can be run with run-mcp.
Maintains a registry file at ~/.mcp-generator/servers.json
"""

import argparse
import json
import sys
from pathlib import Path


def get_registry_path() -> Path:
    """Get the path to the local MCP servers registry."""
    registry_dir = Path.home() / ".mcp-generator"
    registry_dir.mkdir(exist_ok=True)
    return registry_dir / "servers.json"


def load_registry() -> dict:
    """Load the local MCP servers registry."""
    registry_path = get_registry_path()
    if not registry_path.exists():
        return {}

    try:
        with open(registry_path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load registry: {e}")
        return {}


def save_registry(registry: dict) -> None:
    """Save the local MCP servers registry."""
    registry_path = get_registry_path()
    try:
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"❌ Error: Could not save registry: {e}")
        sys.exit(1)


def register_server(server_path: Path) -> None:
    """Register a local MCP server."""
    if not server_path.exists():
        print(f"❌ Error: Path does not exist: {server_path}")
        sys.exit(1)

    # Look for pyproject.toml
    pyproject_path = server_path / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"❌ Error: No pyproject.toml found in {server_path}")
        sys.exit(1)

    # Parse pyproject.toml to get server info
    try:
        import tomli
    except ImportError:
        # Fallback for Python 3.11+
        try:
            import tomllib as tomli
        except ImportError:
            print("❌ Error: tomli/tomllib not available")
            sys.exit(1)

    try:
        with open(pyproject_path, 'rb') as f:
            pyproject = tomli.load(f)
    except Exception as e:
        print(f"❌ Error: Could not parse pyproject.toml: {e}")
        sys.exit(1)

    # Extract server name from entry points
    entry_points = pyproject.get('project', {}).get('entry-points', {}).get('mcp_servers', {})

    if not entry_points:
        print("❌ Error: No mcp_servers entry points found in pyproject.toml")
        print("   Expected: [project.entry-points.\"mcp_servers\"]")
        sys.exit(1)

    # Get the first entry point (should only be one per server)
    server_name = list(entry_points.keys())[0]
    entry_point = entry_points[server_name]

    # Load existing registry
    registry = load_registry()

    # Add/update server entry
    registry[server_name] = {
        'path': str(server_path.resolve()),
        'entry_point': entry_point,
        'name': pyproject.get('project', {}).get('name', server_name),
        'version': pyproject.get('project', {}).get('version', '0.0.0'),
        'description': pyproject.get('project', {}).get('description', ''),
    }

    # Save registry
    save_registry(registry)

    print(f"✅ Registered MCP server: {server_name}")
    print(f"   Path: {server_path.resolve()}")
    print(f"   Entry point: {entry_point}")
    print(f"\nRun with: uv run run-mcp {server_name} --mode stdio")


def unregister_server(server_name: str) -> None:
    """Unregister a local MCP server."""
    registry = load_registry()

    if server_name not in registry:
        print(f"❌ Error: Server '{server_name}' not found in registry")
        print("\nRegistered servers:")
        if registry:
            for name in sorted(registry.keys()):
                print(f"  • {name}")
        else:
            print("  (none)")
        sys.exit(1)

    del registry[server_name]
    save_registry(registry)

    print(f"✅ Unregistered MCP server: {server_name}")


def list_servers() -> None:
    """List all registered local MCP servers."""
    registry = load_registry()

    if not registry:
        print("No MCP servers registered.")
        print(f"\nRegistry location: {get_registry_path()}")
        print("\nTo register a server:")
        print("  uv run register-mcp /path/to/server")
        return

    print("Registered MCP Servers:")
    print("=" * 70)
    for name, info in sorted(registry.items()):
        print(f"\n  • {name}")
        print(f"    Path: {info['path']}")
        print(f"    Entry point: {info['entry_point']}")
        if info.get('description'):
            print(f"    Description: {info['description']}")

    print(f"\n{'=' * 70}")
    print(f"Registry location: {get_registry_path()}")
    print("\nUsage: uv run run-mcp <server_name> [options]")


def main():
    """Main entry point for register-mcp CLI."""
    parser = argparse.ArgumentParser(
        description="Register local MCP servers for use with run-mcp",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Register command
    register_parser = subparsers.add_parser('add', help='Register a new MCP server')
    register_parser.add_argument('path', type=Path, help='Path to the MCP server directory')

    # Unregister command
    unregister_parser = subparsers.add_parser('remove', help='Unregister an MCP server')
    unregister_parser.add_argument('name', help='Name of the server to unregister')

    # List command
    subparsers.add_parser('list', help='List all registered MCP servers')

    # Default to add if path is provided directly
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-') and sys.argv[1] not in ['add', 'remove', 'list']:
        sys.argv.insert(1, 'add')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'add':
        register_server(args.path)
    elif args.command == 'remove':
        unregister_server(args.name)
    elif args.command == 'list':
        list_servers()


if __name__ == '__main__':
    main()
