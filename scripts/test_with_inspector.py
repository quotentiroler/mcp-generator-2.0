#!/usr/bin/env python3
"""
Helper script to test generated MCP servers with the MCP Inspector.

Usage:
    python scripts/test_with_inspector.py [OPTIONS]

Examples:
    # Test with UI mode (default)
    python scripts/test_with_inspector.py

    # Test with CLI mode
    python scripts/test_with_inspector.py --cli

    # List tools only
    python scripts/test_with_inspector.py --cli --method tools/list

    # Call a specific tool
    python scripts/test_with_inspector.py --cli --method tools/call --tool-name get_pet --tool-arg pet_id=1
"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_generated_server() -> Path | None:
    """Find the generated MCP server in the generated_mcp directory."""
    generated_dir = Path("generated_mcp")
    if not generated_dir.exists():
        return None

    # Look for *_mcp_generated.py file
    mcp_files = list(generated_dir.glob("*_mcp_generated.py"))
    if not mcp_files:
        return None

    return mcp_files[0]


def main():
    parser = argparse.ArgumentParser(description="Test generated MCP servers with MCP Inspector")
    parser.add_argument("--cli", action="store_true", help="Use CLI mode instead of UI mode")
    parser.add_argument(
        "--method",
        type=str,
        help="CLI method to call (e.g., tools/list, tools/call, resources/list)",
    )
    parser.add_argument("--tool-name", type=str, help="Tool name for tools/call method")
    parser.add_argument(
        "--tool-arg",
        action="append",
        help="Tool arguments in key=value format (can be used multiple times)",
    )
    parser.add_argument(
        "--env",
        "-e",
        action="append",
        help="Environment variables in KEY=VALUE format (can be used multiple times)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument("--server-path", type=Path, help="Path to MCP server file")

    args = parser.parse_args()

    # Find server
    server_path = args.server_path or find_generated_server()
    if not server_path:
        print("❌ Error: Could not find generated MCP server")
        print("💡 Tip: Run 'uv run generate-mcp' first")
        sys.exit(1)

    if not server_path.exists():
        print(f"❌ Error: Server file not found: {server_path}")
        sys.exit(1)

    print(f"🔍 Testing server: {server_path}")

    # Build inspector command
    cmd = ["npx", "@modelcontextprotocol/inspector"]

    # Add CLI flag if requested
    if args.cli:
        cmd.append("--cli")

    # Add environment variables
    if args.env:
        for env_var in args.env:
            cmd.extend(["-e", env_var])

    # Add server command
    cmd.extend(["python", str(server_path)])

    # Add CLI-specific options
    if args.cli:
        if args.method:
            cmd.extend(["--method", args.method])

        if args.tool_name:
            cmd.extend(["--tool-name", args.tool_name])

        if args.tool_arg:
            for arg in args.tool_arg:
                cmd.extend(["--tool-arg", arg])

        if args.transport and args.transport != "stdio":
            cmd.extend(["--transport", args.transport])

    # Print command
    print(f"🚀 Running: {' '.join(cmd)}\n")

    # Run inspector
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n👋 Inspector stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error running inspector: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
