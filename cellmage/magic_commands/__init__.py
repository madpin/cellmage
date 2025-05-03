"""
Magic command modules for CellMage.

This package contains modules for various kinds of IPython magic commands:
- core: Core functionality for chat, model settings, adapter switching
- history: History management commands
- persistence: Saving and loading conversations
"""

from . import core, history, persistence

__all__ = ["core", "history", "persistence"]
