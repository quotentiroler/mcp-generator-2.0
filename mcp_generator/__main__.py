"""
MCP Generator - Package entry point.

Allows running the generator as a module:
    python -m mcp_generator
"""

from .cli import main

if __name__ == "__main__":
    main()
