"""
Context providers for CellMage.

This package contains implementations of the ContextProvider interface
for different environments.
"""

from .ipython_context_provider import (
    IPythonContextProvider,
    get_ipython_context_provider,
)

__all__ = ["IPythonContextProvider", "get_ipython_context_provider"]
