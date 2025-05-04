"""
Core utility functionality for magic commands.

This module provides foundational support for magic command integrations.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# Common functions that might be used by multiple magic command implementations
def format_tokens_info(tokens_in: int, tokens_out: int) -> str:
    """Format token usage information for display.

    Args:
        tokens_in: Number of input tokens
        tokens_out: Number of output tokens

    Returns:
        Formatted string with token information
    """
    total = tokens_in + tokens_out
    return f"Total: {total} tokens (In: {tokens_in}, Out: {tokens_out})"


def extract_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant metadata from a message for display.

    Args:
        metadata: Message metadata dictionary

    Returns:
        Dictionary with relevant metadata for display
    """
    result = {}

    if not metadata:
        return result

    # Extract common fields
    if "model_used" in metadata:
        result["model"] = metadata["model_used"]

    if "tokens_in" in metadata:
        result["tokens_in"] = metadata["tokens_in"]

    if "tokens_out" in metadata:
        result["tokens_out"] = metadata["tokens_out"]

    if "cost_str" in metadata:
        result["cost"] = metadata["cost_str"]

    return result
