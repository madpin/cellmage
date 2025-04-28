"""
Integration components for various environments.

This module contains integrations with environments like IPython/Jupyter,
including magics and context providers.
"""

try:
    from ..context_providers.ipython_context_provider import IPythonContextProvider
    from .ipython_magic import (
        NotebookLLMMagics,
        load_ipython_extension,
        unload_ipython_extension,
    )

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

if _IPYTHON_AVAILABLE:
    __all__ = [
        "IPythonContextProvider",
        "NotebookLLMMagics",
        "load_ipython_extension",
        "unload_ipython_extension",
    ]
else:
    __all__ = []
