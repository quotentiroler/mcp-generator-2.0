"""
Code generation and rendering.

Split by output artifact; re-exported here so importers keep one entry point.
"""

from .project_files import render_fastmcp_template, render_pyproject_template
from .resources import generate_resource_for_endpoint, render_resource
from .server_module import generate_server_module
from .tools import _render_tool, generate_tool_for_method

__all__ = [
    "_render_tool",
    "generate_resource_for_endpoint",
    "generate_server_module",
    "generate_tool_for_method",
    "render_fastmcp_template",
    "render_pyproject_template",
    "render_resource",
]
