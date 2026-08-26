"""
CLI entry point.

Split into argument definitions, reporting and orchestration.
"""

from .main import main
from .reporting import print_metadata_summary, setup_utf8_console

__all__ = ["main", "print_metadata_summary", "setup_utf8_console"]
