"""
Integration modules for CellMage.

This package contains modules that integrate CellMage with other systems.
"""

# Import the IPython magic modules for easy access
from . import ipython_magic, jira_magic

__all__ = ["ipython_magic", "jira_magic"]
