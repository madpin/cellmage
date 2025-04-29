"""
Integration modules for CellMage.

This package contains modules that integrate CellMage with other systems.
"""

# Import the IPython magic modules for easy access
from . import gitlab_magic, ipython_magic, jira_magic

__all__ = ["ipython_magic", "jira_magic", "gitlab_magic"]
