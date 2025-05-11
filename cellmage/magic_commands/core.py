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


def extract_metadata_for_status(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts model, token, and cost info for status bar display, always using 'model_used' key."""
    result = {}
    if not metadata:
        return result
    # Always use 'model_used' for status bar
    if "model_used" in metadata:
        result["model_used"] = metadata["model_used"]
    elif "model" in metadata:
        result["model_used"] = metadata["model"]
    if "tokens_in" in metadata:
        result["tokens_in"] = metadata["tokens_in"]
    if "tokens_out" in metadata:
        result["tokens_out"] = metadata["tokens_out"]
    if "cost_str" in metadata:
        result["cost_str"] = metadata["cost_str"]
    return result


def extract_history_stats(history):
    """
    Extracts token and model usage statistics from a conversation history.

    Args:
        history: Iterable of message objects with 'role', 'metadata', and 'content'.

    Returns:
        dict: {tokens_in, tokens_out, models_used, estimated_messages}
    """
    total_tokens_in = 0
    total_tokens_out = 0
    models_used = {}
    estimated_messages = 0

    for msg in history:
        if hasattr(msg, "metadata") and msg.metadata:
            tokens_in = msg.metadata.get("tokens_in", 0)
            tokens_out = msg.metadata.get("tokens_out", 0)
            if msg.role in ("user", "system"):
                total_tokens_in += tokens_in
            elif msg.role == "assistant":
                total_tokens_out += tokens_out
            model = msg.metadata.get("model_used", "")
            if model and msg.role == "assistant":
                models_used[model] = models_used.get(model, 0) + 1
        elif hasattr(msg, "content") and msg.content:
            # Fallback: estimate tokens if no metadata
            from cellmage.utils.token_utils import count_tokens

            estimated_tokens = count_tokens(msg.content)
            if msg.role in ("user", "system"):
                total_tokens_in += estimated_tokens
            elif msg.role == "assistant":
                total_tokens_out += estimated_tokens
            estimated_messages += 1

    return {
        "tokens_in": float(total_tokens_in),
        "tokens_out": float(total_tokens_out),
        "models_used": models_used,
        "estimated_messages": estimated_messages,
    }


def get_last_assistant_metadata(history):
    """
    Returns the metadata dict from the last assistant message in a history, or an empty dict.
    """
    last_assistant = next(
        (m for m in reversed(history) if getattr(m, "role", None) == "assistant"), None
    )
    return (
        last_assistant.metadata
        if last_assistant and hasattr(last_assistant, "metadata") and last_assistant.metadata
        else {}
    )
