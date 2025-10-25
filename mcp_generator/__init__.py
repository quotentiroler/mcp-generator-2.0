"""
MCP Generator Package.

A modular code generator for creating FastMCP 2.x servers from OpenAPI specifications.

Main modules:
- cli: Command-line interface and entry point
- generator: Core orchestration and generation logic
- introspection: API discovery and metadata extraction
- renderers: Code generation and template rendering
- models: Data structures for configuration and specs
- utils: Helper functions for sanitization and formatting
- templates: Template generators for middleware and auth
- writers: File writing and directory management
- test_generator: Generates authentication flow demonstration tests

Usage:
    python -m mcp_generator
"""

from .cli import main
from .generator import generate_all, generate_main_composition_server, generate_modular_servers
from .introspection import get_api_metadata, get_api_modules, get_security_config
from .models import ApiMetadata, ModuleSpec, ParameterInfo, SecurityConfig, ToolSpec
from .test_generator import generate_auth_flow_tests, generate_tool_tests
from .utils import get_pydantic_model_schema, sanitize_name

__version__ = "1.0.0"

__all__ = [
    "main",
    "generate_all",
    "generate_modular_servers",
    "generate_main_composition_server",
    "get_api_modules",
    "get_api_metadata",
    "get_security_config",
    "ApiMetadata",
    "SecurityConfig",
    "ModuleSpec",
    "ParameterInfo",
    "ToolSpec",
    "sanitize_name",
    "get_pydantic_model_schema",
    "generate_auth_flow_tests",
    "generate_tool_tests",
]
