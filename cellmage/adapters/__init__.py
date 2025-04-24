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

# Try to import LiteLLMAdapter if litellm is available, but it's now optional
try:
    from .llm_client import LiteLLMAdapter
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False

# Export the DirectLLMAdapter as the default
if _DIRECT_AVAILABLE:
    __all__ = ["DirectLLMAdapter"]
    
    # Also export LiteLLMAdapter if available, but not as the default
    if _LITELLM_AVAILABLE:
        __all__.append("LiteLLMAdapter")
elif _LITELLM_AVAILABLE:
    # Fall back to LiteLLMAdapter if direct isn't available
    __all__ = ["LiteLLMAdapter"]
else:
    __all__ = []