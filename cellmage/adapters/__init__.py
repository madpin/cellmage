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

# Export the DirectLLMAdapter as the default
if _DIRECT_AVAILABLE:
    __all__ = ["DirectLLMAdapter"]
else:
    __all__ = []