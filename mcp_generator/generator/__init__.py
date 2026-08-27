"""
Core orchestration.

Split by generation stage; re-exported here so importers keep one entry point.
"""

from .composition import generate_main_composition_server
from .modules import generate_modular_servers
from .orchestration import generate_all

__all__ = [
    "generate_all",
    "generate_main_composition_server",
    "generate_modular_servers",
]
