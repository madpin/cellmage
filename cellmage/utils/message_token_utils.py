"""
Utilities for counting tokens in messages and conversations.

This module provides functions for accurately counting tokens in messages and conversations,
using either the LLM client's capabilities or falling back to metadata/estimates.
"""

import logging
from typing import Any, Dict, List

from ..models import Message
from ..utils.token_utils import count_tokens

# Create a logger
logger = logging.getLogger(__name__)


def count_tokens_with_llm_client(manager, messages: List[Message]) -> Dict[str, Any]:
    """
    Count tokens using the LLM client's accurate tokenizer if available.

    Args:
        manager: The ChatManager instance with llm_client
        messages: List of messages to count tokens for

    Returns:
        Dict with token counts for total, user, assistant, and system roles
    """
    result = {"total": 0, "user": 0, "assistant": 0, "system": 0}

    try:
        if manager.llm_client and hasattr(manager.llm_client, "count_tokens_for_messages"):
            # Get total tokens for all messages
            result["total"] = manager.llm_client.count_tokens_for_messages(messages)

            # Count tokens by role
            for msg in messages:
                role = msg.role if hasattr(msg, "role") else "unknown"
                msg_tokens = manager.llm_client.count_tokens_for_messages([msg])

                if role in result:
                    result[role] += msg_tokens

            return result
    except Exception as e:
        logger.debug(f"Error counting tokens with LLM client: {e}")

    # If we get here, counting with the client failed
    return None


def get_token_counts(manager, messages: List[Message]) -> Dict[str, Any]:
    """
    Count tokens using the best available method.

    First tries the LLM client's accurate counter, then falls back to metadata.

    Args:
        manager: The ChatManager instance
        messages: List of messages to count tokens for

    Returns:
        Dict with token counts for total, user, assistant, and system roles
    """
    # First try using the LLM client for accurate counts
    result = count_tokens_with_llm_client(manager, messages)

    # If that worked, return it
    if result:
        return result

    # Otherwise, fall back to metadata counting
    result = {"total": 0, "user": 0, "assistant": 0, "system": 0}

    for msg in messages:
        if not msg.metadata:
            continue

        role = msg.role if hasattr(msg, "role") else "unknown"

        # Extract tokens from metadata
        if role == "user" or role == "system":
            tokens = msg.metadata.get("tokens_in", 0)
            result["user"] += tokens if role == "user" else 0
            result["system"] += tokens if role == "system" else 0
        elif role == "assistant":
            tokens = msg.metadata.get("tokens_out", 0)
            result["assistant"] += tokens

        # If there's a total_tokens field, use that too
        total = msg.metadata.get("total_tokens", 0)
        if total > 0:
            result["total"] += total

    # If no total was found in metadata, sum the role counts
    if result["total"] == 0:
        result["total"] = result["user"] + result["assistant"] + result["system"]

    return result


def estimate_message_tokens(message: Message) -> Dict[str, int]:
    """
    Estimate token counts for a single message when no other method is available.

    Args:
        message: Message to count tokens for

    Returns:
        Dict with estimated token counts
    """
    role = message.role if hasattr(message, "role") else "unknown"
    content = message.content if hasattr(message, "content") else ""

    # Use utility function from token_utils
    estimated_tokens = count_tokens(content)

    result = {"total": estimated_tokens, role: estimated_tokens}

    return result
