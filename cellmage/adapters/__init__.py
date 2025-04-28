"""
Adapters for integrating with external services and libraries.

This module contains implementations of interfaces for adapting
external libraries and APIs to work with the cellmage library.
"""

try:
    from .direct_client import DirectLLMAdapter

    _DIRECT_AVAILABLE = True
except ImportError:
    _DIRECT_AVAILABLE = False

try:
    from .langchain_client import LangChainAdapter

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

# Export available adapters
__all__ = []
if _DIRECT_AVAILABLE:
    __all__.append("DirectLLMAdapter")
if _LANGCHAIN_AVAILABLE:
    __all__.append("LangChainAdapter")
