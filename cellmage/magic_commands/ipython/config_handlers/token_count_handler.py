"""
Token counting handler for the %llm_config magic command.

This module handles token counting arguments for the %llm_config magic command.
"""

import logging
from typing import Any, Dict, List

from cellmage.magic_commands.ipython.config_handlers.base_config_handler import (
    BaseConfigHandler,
)
from cellmage.models import Message
from cellmage.utils.message_token_utils import get_token_counts

# Create a logger
logger = logging.getLogger(__name__)


class TokenCountHandler(BaseConfigHandler):
    """Handler for token counting arguments in the %llm_config magic."""

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle token counting arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any token-related action was performed, False otherwise.
        """
        action_taken = False

        # Check if we should show token count
        show_tokens = (
            hasattr(args, "tokens") and args.tokens or hasattr(args, "token") and args.token
        )

        if show_tokens:
            action_taken = True
            try:
                self._show_token_count(manager)
            except Exception as e:
                logger.exception(f"Error showing token count: {e}")
                print(f"❌ Error showing token count: {e}")

        return action_taken

    def _show_token_count(self, manager):
        """
        Show the token count for the current conversation.

        Args:
            manager: The ChatManager instance.
        """
        if manager and hasattr(manager, "conversation_manager") and manager.conversation_manager:
            # Get the conversation history
            history = manager.conversation_manager.get_messages()
        else:
            print("⚠️ No active conversation history found.")
            return

        # Get token counts using the token manager module for consistent counting
        token_data = get_token_counts(manager, history)

        # Format and display token counts
        self._display_token_counts(token_data)

    def _count_tokens(self, messages: List[Message], manager) -> Dict[str, Any]:
        """
        Count tokens in the conversation history.

        Args:
            messages: List of Message objects in the conversation history
            manager: The ChatManager instance

        Returns:
            Dict containing token counts and related information
        """
        result = {"user": 0, "assistant": 0, "system": 0, "total": 0, "messages": []}

        # Use the token counter from the LLM client if available
        if manager.llm_client and hasattr(manager.llm_client, "count_tokens_for_messages"):
            try:
                total_tokens = manager.llm_client.count_tokens_for_messages(messages)
                result["total"] = total_tokens

                # Count tokens per message if possible
                for msg in messages:
                    msg_tokens = manager.llm_client.count_tokens_for_messages([msg])
                    # Access role attribute directly instead of using get()
                    role = msg.role if hasattr(msg, "role") else "unknown"
                    result[role] += msg_tokens

                    # Store individual message token counts - use direct attribute access
                    content = msg.content if hasattr(msg, "content") else ""
                    result["messages"].append(
                        {
                            "role": role,
                            "content_snippet": (
                                (content[:30].replace("\n", " ") + "...")
                                if len(content) > 30
                                else content.replace("\n", " ")
                            ),
                            "tokens": msg_tokens,
                        }
                    )

            except Exception as e:
                logger.warning(f"Error counting tokens with LLM client: {e}")
                print("⚠️ Approximating token count (error with token counter)")
                # Fallback to approximation
                result = self._approximate_token_count(messages)
        else:
            # Fallback to approximation
            result = self._approximate_token_count(messages)

        return result

    def _approximate_token_count(self, messages: List[Message]) -> Dict[str, Any]:
        """
        Approximate token count when a precise counter isn't available.

        Args:
            messages: List of Message objects in the conversation history

        Returns:
            Dict containing approximated token counts
        """
        result = {
            "user": 0,
            "assistant": 0,
            "system": 0,
            "total": 0,
            "messages": [],
            "is_approximate": True,
        }

        # Rough approximation: ~4 characters per token
        for msg in messages:
            # Access attributes directly instead of using get()
            role = msg.role if hasattr(msg, "role") else "unknown"
            content = msg.content if hasattr(msg, "content") else ""

            # Approximate token count for this message
            token_count = len(content) // 4

            # Add to role-specific and total counts
            if role in result:
                result[role] += token_count
            result["total"] += token_count

            # Store individual message details
            result["messages"].append(
                {
                    "role": role,
                    "content_snippet": (content[:30] + "...") if len(content) > 30 else content,
                    "tokens": token_count,
                }
            )

        return result

    def _display_token_counts(self, token_counts: Dict[str, Any]):
        """
        Format and display token count information.

        Args:
            token_counts: Dictionary containing token count information
        """
        is_approximate = token_counts.get("is_approximate", False)

        # Print header
        print("\n📊 Token Count Summary" + (" (Approximate)" if is_approximate else ""))
        print("=" * 50)

        # Print total counts by role
        print(f"🔢 Total tokens: {token_counts['total']}")
        print(f"👤 User tokens: {token_counts['user']}")
        print(f"🤖 Assistant tokens: {token_counts['assistant']}")
        print(f"⚙️ System tokens: {token_counts['system']}")

        # Print message details if available and not too many
        messages = token_counts.get("messages", [])
        if messages and len(messages) <= 10:  # Only show details if 10 or fewer messages
            print("\n📝 Message Details:")
            print("-" * 50)
            for i, msg in enumerate(messages, 1):
                print(f'{i}. {msg["role"]}: {msg["tokens"]} tokens - "{msg["content_snippet"]}"')

        print("=" * 50)
