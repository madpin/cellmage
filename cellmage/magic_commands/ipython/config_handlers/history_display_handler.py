"""
History display handler for the %llm_config magic command.

This module handles history-related arguments for the %llm_config magic command.
"""

import datetime
import logging
from typing import Any, Dict, List

from cellmage.magic_commands.core import extract_metadata_for_status
from cellmage.models import Message

from ....utils.token_utils import count_tokens
from .base_config_handler import BaseConfigHandler

# Create a logger
logger = logging.getLogger(__name__)


class HistoryDisplayHandler(BaseConfigHandler):
    """Handler for history-related configuration arguments."""

    def _count_tokens(self, messages: List[Message], manager) -> Dict[str, Any]:
        """
        Count tokens in the conversation history.

        Args:
            messages: List of Message objects in the conversation history
            manager: The ChatManager instance

        Returns:
            Dict containing token counts and related information
        """
        result = {
            "user": 0,
            "assistant": 0,
            "system": 0,
            "total": 0,
            "messages": [],
            "is_approximate": False,
        }

        # Use the token counter from the LLM client if available
        if manager.llm_client and hasattr(manager.llm_client, "count_tokens_for_messages"):
            try:
                total_tokens = manager.llm_client.count_tokens_for_messages(messages)
                result["total"] = total_tokens

                # Count tokens per message if possible
                for msg in messages:
                    msg_tokens = manager.llm_client.count_tokens_for_messages([msg])
                    role = msg.role if hasattr(msg, "role") else "unknown"
                    if role in result:
                        result[role] += msg_tokens

                    # Store individual message token counts
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

        # Use count_tokens utility for better approximation
        for msg in messages:
            role = msg.role if hasattr(msg, "role") else "unknown"
            content = msg.content if hasattr(msg, "content") else ""

            # Get token count for this message
            token_count = count_tokens(content)

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

    def handle_args(self, args: Any, manager: Any) -> bool:
        """
        Handle history-related arguments for the %llm_config magic.

        Args:
            args: The parsed arguments from the magic command.
            manager: The ChatManager instance.

        Returns:
            bool: True if any history-related action was performed, False otherwise.
        """
        action_taken = False

        if hasattr(args, "clear_history") and args.clear_history:
            action_taken = True
            manager.clear_history()
            logger.info("✅ Chat history cleared.")
            print("✅ Chat history cleared.")

        if hasattr(args, "show_history") and args.show_history:
            action_taken = True

            history = manager.get_history()
            logger.debug(f"DEBUG: Retrieved {len(history)} total messages")

            # Detailed debug of message types and integration messages
            role_counts = {}
            source_counts = {}
            integration_metadata = []

            for i, msg in enumerate(history):
                # Count roles
                role = msg.role
                role_counts[role] = role_counts.get(role, 0) + 1

                # Track integration sources
                if msg.metadata and "source" in msg.metadata:
                    source = msg.metadata.get("source", "")
                    if source:
                        source_counts[source] = source_counts.get(source, 0) + 1
                        # Collect details about this integration message
                        integration_metadata.append(
                            {
                                "index": i,
                                "source": source,
                                "type": msg.metadata.get("type", "unknown"),
                                "role": msg.role,
                            }
                        )

            # Get accurate token counts using the LLM client if available
            token_counts = self._count_tokens(history, manager)
            total_tokens = token_counts["total"]
            total_tokens_in = token_counts["user"] + token_counts["system"]
            total_tokens_out = token_counts["assistant"]
            estimated_messages = token_counts.get("is_approximate", False)

            # Combining source_counts and role_counts for readable output
            integration_counts = source_counts

            # Print history header with summary information
            print("📜 Conversation History")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"• Messages: {len(history)}")

            # Format token information
            token_summary = f"• 📊 Total: {total_tokens} tokens"
            if total_tokens_in > 0 or total_tokens_out > 0:
                token_summary += f" (Input: {total_tokens_in} • Output: {total_tokens_out})"
            if estimated_messages > 0:
                token_summary += f" (includes {estimated_messages} estimated message{'s' if estimated_messages > 1 else ''})"
            print(token_summary)

            if not history:
                print("(No messages in history)")
            else:
                # First, display a summary of models used in the conversation
                models_used = {}
                for msg in history:
                    if msg.metadata:
                        meta = extract_metadata_for_status(msg.metadata)
                        model = meta.get("model_used") or meta.get("model") or ""
                        if model and msg.role == "assistant":
                            models_used[model] = models_used.get(model, 0) + 1

                if models_used:
                    model_str = "• 🤖 Models: " + ", ".join(
                        f"{model} ({count})" for model, count in models_used.items()
                    )
                    print(model_str)

                # Count message types and integrations
                role_counts = {}
                integration_counts = {}
                for msg in history:
                    # Count by role
                    role_counts[msg.role] = role_counts.get(msg.role, 0) + 1

                    # Count integration sources
                    if msg.metadata and "source" in msg.metadata:
                        source = msg.metadata.get("source", "")
                        if source:
                            integration_counts[source] = integration_counts.get(source, 0) + 1

                # Print message type summary
                if role_counts:
                    role_summary = "• Message types: " + ", ".join(
                        f"{role} ({count})" for role, count in role_counts.items()
                    )
                    print(role_summary)

                # Print integration summary if any
                if integration_counts:
                    integration_summary = "• Integrations: " + ", ".join(
                        f"{source} ({count})" for source, count in integration_counts.items()
                    )
                    print(integration_summary)

                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # Display the messages with improved formatting
                for i, msg in enumerate(history):
                    meta = extract_metadata_for_status(msg.metadata) if msg.metadata else {}
                    model_used = meta.get("model_used") or meta.get("model") or ""
                    cost_str = meta.get("cost_str") or meta.get("cost") or ""

                    # Use accurate token counts from the token_counts dictionary
                    # Find the matching message in token_counts
                    msg_tokens = 0
                    is_estimated = False

                    # Find this message in our token count results
                    for msg_data in token_counts.get("messages", []):
                        if msg_data.get("role") == msg.role and msg_data.get(
                            "content_snippet", ""
                        ).startswith(msg.content[:20].replace("\n", " ")):
                            msg_tokens = msg_data.get("tokens", 0)
                            is_estimated = token_counts.get("is_approximate", False)
                            break

                    tokens_in = 0
                    tokens_out = 0
                    if msg.role == "user" or msg.role == "system":
                        tokens_in = msg_tokens
                    elif msg.role == "assistant":
                        tokens_out = msg_tokens

                    # Get integration source if available
                    source = meta.get("source", "")
                    source_type = meta.get("type", "")

                    # Mark any message with a source as an integration message
                    is_integration = bool(source)

                    # Determine role icon and create a formatted role label
                    role_icon = ""
                    if msg.role == "system":
                        role_icon = "⚙️"
                    elif msg.role == "user":
                        role_icon = "👤"
                    elif msg.role == "assistant":
                        role_icon = "🤖"
                    else:
                        role_icon = "📄"

                    # Create role label with possible integration source info
                    role_label = f"[{i}] {role_icon} {msg.role.upper()}"

                    # Add integration source info to the label with more prominent styling
                    if source:
                        integration_icon = "🔌"
                        if source.lower() == "github":
                            integration_icon = "🐙"  # GitHub octopus icon
                        elif source.lower() == "gitlab":
                            integration_icon = "🦊"  # GitLab fox icon
                        elif source.lower() == "jira":
                            integration_icon = "📋"  # Jira ticket icon
                        elif source.lower() == "confluence":
                            integration_icon = "📘"  # Confluence docs icon

                        # Add integration source info to the label
                        role_label += f" {integration_icon} {source.upper()}"
                        if source_type:
                            role_label += f" ({source_type})"

                    # Display token info based on role
                    token_info = ""
                    if msg.role == "user" and tokens_in > 0:
                        token_info = f"📥 {tokens_in} tokens{' (est.)' if is_estimated else ''}"
                    elif msg.role == "assistant" and tokens_out > 0:
                        token_info = f"📤 {tokens_out} tokens{' (est.)' if is_estimated else ''}"
                        if cost_str:
                            token_info += f" • {cost_str}"

                    # Print the message header with role and tokens
                    if token_info:
                        print(f"{role_label}  {token_info}")
                    else:
                        print(role_label)

                    # Format the message content with proper handling of long text
                    content_preview = msg.content.replace("\n", " ").strip()
                    # For integration messages, make the content preview slightly longer
                    preview_length = 150 if is_integration else 100

                    if len(content_preview) > preview_length:
                        content_preview = content_preview[: preview_length - 3] + "..."

                    # Print content with indentation
                    print(f"  {content_preview}")

                    # Format metadata in a cleaner way
                    meta_items = []

                    # Add source-specific ID if available
                    if source:
                        for key, value in meta.items():
                            if key.endswith("_id") and value and key != "cell_id":
                                meta_items.append(f"{source} ID: {value}")
                                break

                    # Add other metadata
                    if msg.id:
                        meta_items.append(f"ID: ...{msg.id[-6:]}")
                    if msg.cell_id:
                        meta_items.append(f"Cell: {msg.cell_id[-8:]}")
                    if msg.execution_count:
                        meta_items.append(f"Exec: {msg.execution_count}")
                    if model_used and msg.role == "assistant":
                        meta_items.append(f"Model: {model_used}")
                    if msg.is_snippet:
                        meta_items.append("Snippet: Yes")
                    if "timestamp" in meta:
                        try:
                            ts = datetime.datetime.fromisoformat(meta["timestamp"])
                            meta_items.append(f"Time: {ts.strftime('%H:%M:%S')}")
                        except (ValueError, TypeError):
                            pass

                    # Ensure source is always shown
                    if source and not any(item.startswith(f"{source} ID:") for item in meta_items):
                        meta_items.append(f"Source: {source}")

                    if meta_items:
                        meta_str = "  └─ " + ", ".join(meta_items)
                        print(meta_str)

                    # Add separator between messages
                    if i < len(history) - 1:
                        print("  ·····")

                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return action_taken
