"""
Integration modules for CellMage.

This package provides integrations with various third-party services and systems.
Each integration module can define a `load_ipython_extension(ipython)` function to
register itself with IPython when CellMage is loaded.
"""

import pkgutil
import sys

# Dynamically discover all integration modules
__all__ = []
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name != "__pycache__":
        __all__.append(module_name)
