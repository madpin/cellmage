"""
History management commands for CellMage.

This module provides the history management and persistence commands for CellMage.
"""

import logging
from typing import Any, Dict, List

from ..chat_manager import ChatManager
from ..conversation_manager import ConversationManager
from ..exceptions import PersistenceError, ResourceNotFoundError

# Logging setup
logger = logging.getLogger(__name__)


def handle_history_commands(args, manager: ChatManager) -> bool:
    """
    Handle history-related arguments.

    Args:
        args: The parsed argument namespace
        manager: Chat manager instance

    Returns:
        True if any action was taken, False otherwise
    """
    action_taken = False

    if args.clear_history:
        action_taken = True
        manager.clear_history()
        print("✅ Chat history cleared.")

    if args.show_history:
        action_taken = True
        history = manager.get_history()

        # Calculate total tokens for all messages
        total_tokens_in = 0
        total_tokens_out = 0
        total_tokens = 0

        # Calculate cumulative token counts
        for msg in history:
            if msg.metadata:
                total_tokens_in += msg.metadata.get("tokens_in", 0)
                total_tokens_out += msg.metadata.get("tokens_out", 0)
                msg_total = msg.metadata.get("total_tokens", 0)
                if msg_total > 0:
                    total_tokens += msg_total

        # If no total_tokens were found, calculate from in+out
        if total_tokens == 0:
            total_tokens = total_tokens_in + total_tokens_out

        # Print history header with summary information
        print("📜 Conversation History")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"• Messages: {len(history)}")

        # Format token information
        token_summary = f"• 📊 Total: {total_tokens} tokens"
        if total_tokens_in > 0 or total_tokens_out > 0:
            token_summary += f" (Input: {total_tokens_in} • Output: {total_tokens_out})"
        print(token_summary)

        if not history:
            print("(No messages in history)")
        else:
            # First, display a summary of models used in the conversation
            models_used = {}
            for msg in history:
                if msg.metadata and "model_used" in msg.metadata:
                    model = msg.metadata.get("model_used", "")
                    if model:
                        models_used[model] = models_used.get(model, 0) + 1

            if models_used:
                model_str = "• 🤖 Models: " + ", ".join(
                    f"{model} ({count})" for model, count in models_used.items()
                )
                print(model_str)

            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # Display the messages with improved formatting
            for i, msg in enumerate(history):
                # Get metadata values with defaults
                tokens_in = msg.metadata.get("tokens_in", 0) if msg.metadata else 0
                tokens_out = msg.metadata.get("tokens_out", 0) if msg.metadata else 0
                model_used = msg.metadata.get("model_used", "") if msg.metadata else ""
                cost_str = msg.metadata.get("cost_str", "") if msg.metadata else ""

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

                role_label = f"[{i}] {role_icon} {msg.role.upper()}"

                # Display token info based on role
                token_info = ""
                if msg.role == "user" and tokens_in > 0:
                    token_info = f"📥 {tokens_in} tokens"
                elif msg.role == "assistant" and tokens_out > 0:
                    token_info = f"📤 {tokens_out} tokens"
                    if cost_str:
                        token_info += f" • {cost_str}"

                # Print the message header with role and tokens
                if token_info:
                    print(f"{role_label}  {token_info}")
                else:
                    print(role_label)

                # Format the message content with proper handling of long text
                content_preview = msg.content.replace("\n", " ").strip()
                if len(content_preview) > 100:
                    content_preview = content_preview[:97] + "..."
                print(f"  {content_preview}")

                # Format metadata in a cleaner way
                meta_items = []
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

                if meta_items:
                    meta_str = "  └─ " + ", ".join(meta_items)
                    print(meta_str)

                # Add separator between messages
                if i < len(history) - 1:
                    print("  ·····")

            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return action_taken


def handle_persistence_commands(args, manager: ChatManager) -> bool:
    """
    Handle persistence-related arguments.

    Args:
        args: The parsed argument namespace
        manager: Chat manager instance

    Returns:
        True if any action was taken, False otherwise
    """
    action_taken = False

    if args.list_sessions:
        action_taken = True
        try:
            # Check which method is available for listing sessions
            sessions = []
            method_used = None

            if hasattr(manager, "list_saved_sessions"):
                sessions = manager.list_saved_sessions()
                method_used = "list_saved_sessions"
            elif hasattr(manager, "list_conversations"):
                sessions = manager.list_conversations()
                method_used = "list_conversations"
            elif hasattr(manager, "history_manager") and hasattr(
                manager.history_manager, "list_saved_conversations"
            ):
                sessions = manager.history_manager.list_saved_conversations()
                method_used = "history_manager.list_saved_conversations"
            else:
                raise AttributeError(
                    "No method found for listing sessions. Make sure a conversations directory exists."
                )

            # Format the output in a user-friendly way
            print("══════════════════════════════════════════════════════════")
            print("  📋 Saved Sessions")
            print("══════════════════════════════════════════════════════════")

            if sessions:
                for session in sorted(sessions):
                    print(f"  • {session}")
                print("──────────────────────────────────────────────────────────")
                print(f"  Total: {len(sessions)} session(s)")
                print("  Use: %llm_config --load SESSION_NAME to load a session")
            else:
                print("  No saved sessions found.")
                if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                    print(f"  Sessions directory: {manager.settings.conversations_dir}")
                print("  Use: %llm_config --save SESSION_NAME to save the current conversation")

            print("══════════════════════════════════════════════════════════")
            logger.debug(f"Listed {len(sessions)} sessions using {method_used}")
        except Exception as e:
            print(f"❌ Error listing saved sessions: {e}")
            if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                conversations_dir = manager.settings.conversations_dir
                print(f"  Please make sure the directory exists: {conversations_dir}")
                # Try to check if the directory exists
                import os

                if not os.path.exists(conversations_dir):
                    print(
                        f"  ℹ️ The conversations directory does not exist. Creating it at: {conversations_dir}"
                    )
                    try:
                        os.makedirs(conversations_dir, exist_ok=True)
                        print("  ✅ Created conversations directory successfully.")
                    except Exception as mkdir_error:
                        print(f"  ❌ Failed to create conversations directory: {mkdir_error}")

    # Handle auto-save configuration
    if hasattr(args, "auto_save") and args.auto_save:
        action_taken = True
        try:
            manager.settings.auto_save = True
            # Get absolute path for better user experience
            conversations_dir = os.path.abspath(manager.settings.conversations_dir)
            print("══════════════════════════════════════════════════════════")
            print("  🔄 Auto-Save Enabled")
            print("══════════════════════════════════════════════════════════")
            print(f"  • Conversations will be saved to: {conversations_dir}")

            # Check if directory exists, create if not
            if not os.path.exists(conversations_dir):
                print("  • Directory doesn't exist, creating it now...")
                try:
                    os.makedirs(conversations_dir, exist_ok=True)
                    print("  ✅ Directory created successfully.")
                except Exception as mkdir_error:
                    print(f"  ❌ Failed to create directory: {mkdir_error}")

            print("══════════════════════════════════════════════════════════")
        except Exception as e:
            print(f"❌ Error enabling auto-save: {e}")

    if hasattr(args, "no_auto_save") and args.no_auto_save:
        action_taken = True
        try:
            manager.settings.auto_save = False
            print("══════════════════════════════════════════════════════════")
            print("  🔄 Auto-Save Disabled")
            print("══════════════════════════════════════════════════════════")
            print("  • Conversations will not be saved automatically.")
            print("  • Use %llm_config --save to manually save conversations.")
            print("══════════════════════════════════════════════════════════")
        except Exception as e:
            print(f"❌ Error disabling auto-save: {e}")

    if args.load:
        action_taken = True
        try:
            # Check which method is available for loading sessions
            session_id = args.load

            print("══════════════════════════════════════════════════════════")
            print(f"  📂 Loading Session: {session_id}")
            print("══════════════════════════════════════════════════════════")

            if hasattr(manager, "load_session"):
                manager.load_session(session_id)
                method = "load_session"
            elif hasattr(manager, "load_conversation"):
                manager.load_conversation(session_id)
                method = "load_conversation"
            elif hasattr(manager, "history_manager") and hasattr(
                manager.history_manager, "load_conversation"
            ):
                manager.history_manager.load_conversation(session_id)
                method = "history_manager.load_conversation"
            else:
                raise AttributeError("No method found for loading sessions")

            # Try to get history length after loading
            try:
                history = manager.get_history()
                print(f"  ✅ Session loaded successfully using '{method}'")
                print(f"  • Messages: {len(history)}")
            except Exception:
                print(f"  ✅ Session loaded successfully using '{method}'")

            print("══════════════════════════════════════════════════════════")

        except ResourceNotFoundError:
            print(f"  ❌ Session '{session_id}' not found.")
            # Try to list available sessions for user convenience
            if hasattr(manager, "list_saved_sessions") or hasattr(manager, "list_conversations"):
                print("  Available sessions:")
                try:
                    if hasattr(manager, "list_saved_sessions"):
                        sessions = manager.list_saved_sessions()
                    elif hasattr(manager, "list_conversations"):
                        sessions = manager.list_conversations()

                    # Show up to 5 available sessions
                    if sessions:
                        for i, session in enumerate(sorted(sessions)[:5]):
                            print(f"  • {session}")
                        if len(sessions) > 5:
                            print(f"  • ... and {len(sessions) - 5} more")
                except Exception:
                    pass
            print("══════════════════════════════════════════════════════════")
        except PersistenceError as e:
            print(f"  ❌ Error loading session: {e}")
            print("══════════════════════════════════════════════════════════")
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            print("══════════════════════════════════════════════════════════")

    # Save needs to be after load/clear etc.
    if args.save:
        action_taken = True
        try:
            from pathlib import Path

            print("══════════════════════════════════════════════════════════")
            print("  💾 Saving Session")
            print("══════════════════════════════════════════════════════════")

            # Convert True to None for default behavior if --save was used without argument
            filename = args.save if isinstance(args.save, str) else None
            if filename is not None:
                print(f"  • Name: {filename}")

            # Check which method is available for saving sessions
            if hasattr(manager, "save_session"):
                save_path = manager.save_session(identifier=filename)
                method = "save_session"
            elif hasattr(manager, "save_conversation"):
                save_path = manager.save_conversation(filename)
                method = "save_conversation"
            elif hasattr(manager, "history_manager") and hasattr(
                manager.history_manager, "save_conversation"
            ):
                save_path = manager.history_manager.save_conversation(filename)
                method = "history_manager.save_conversation"
            else:
                raise AttributeError("No method found for saving sessions")

            # Make the path more user-friendly by showing relative path if inside conversations_dir
            try:
                if hasattr(manager.settings, "conversations_dir"):
                    conv_dir = Path(manager.settings.conversations_dir).resolve()
                    file_path = Path(save_path).resolve()
                    if str(file_path).startswith(str(conv_dir)):
                        # Show path relative to conversations_dir
                        rel_path = file_path.relative_to(conv_dir)
                        display_path = f"{conv_dir.name}/{rel_path}"
                    else:
                        display_path = str(file_path)
                else:
                    display_path = save_path
            except Exception:
                # Fallback to just the filename if the above fails
                display_path = Path(save_path).name

            print(f"  ✅ Session saved successfully using '{method}'")
            print(f"  • Path: {display_path}")
            print("══════════════════════════════════════════════════════════")

        except PersistenceError as e:
            print(f"  ❌ Error saving session: {e}")
            print("══════════════════════════════════════════════════════════")
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            # Check if conversations directory exists
            if hasattr(manager, "settings") and hasattr(manager.settings, "conversations_dir"):
                if not os.path.exists(manager.settings.conversations_dir):
                    print(
                        f"  The conversations directory does not exist: {manager.settings.conversations_dir}"
                    )
                    print(
                        "  Try creating it manually or use %llm_config --auto-save to create it automatically."
                    )
            print("══════════════════════════════════════════════════════════")

    return action_taken


def convert_to_conversation_manager(manager: ChatManager) -> ConversationManager:
    """
    Convert a ChatManager to use a ConversationManager for SQLite-based storage.

    Args:
        manager: Chat manager instance

    Returns:
        ConversationManager instance with data from ChatManager
    """
    # Create new conversation manager
    conversation_manager = ConversationManager(context_provider=manager.context_provider)

    # Copy messages from the chat manager's history
    if hasattr(manager, "history_manager") and hasattr(manager.history_manager, "get_history"):
        messages = manager.history_manager.get_history()
        for msg in messages:
            conversation_manager.add_message(msg)

    return conversation_manager


def get_conversation_statistics(conversation_manager: ConversationManager) -> Dict[str, Any]:
    """
    Get statistics about stored conversations.

    Args:
        conversation_manager: ConversationManager instance

    Returns:
        Dictionary with detailed statistics about stored conversations
    """
    try:
        stats = conversation_manager.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting conversation statistics: {e}")
        return {"error": str(e), "total_conversations": 0, "total_messages": 0}


def search_conversations(
    conversation_manager: ConversationManager, query: str, limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for conversations by content.

    Args:
        conversation_manager: ConversationManager instance
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of matching conversations
    """
    try:
        return conversation_manager.search_conversations(query, limit)
    except Exception as e:
        logger.error(f"Error searching conversations: {e}")
        return []


def format_conversation_summary(conversation: Dict[str, Any]) -> str:
    """
    Format a conversation summary for display.

    Args:
        conversation: Conversation metadata dictionary

    Returns:
        Formatted string representation
    """
    # Extract basic info with defaults
    conv_id = conversation.get("id", "unknown")
    name = conversation.get("name", "Unnamed")
    message_count = conversation.get("message_count", 0)
    timestamp = conversation.get("timestamp")
    model_name = conversation.get("model_name", "unknown")
    persona_name = conversation.get("persona_name", "none")
    total_tokens = conversation.get("total_tokens", 0)
    tags = conversation.get("tags", [])

    # Format date
    date_str = "unknown date"
    if timestamp:
        try:
            from datetime import datetime

            date = datetime.fromtimestamp(timestamp)
            date_str = date.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    # Build summary
    summary = [f"Conversation: {name} ({conv_id[:8]}...)"]
    summary.append(f"Date: {date_str}")
    summary.append(f"Messages: {message_count}")

    if model_name and model_name != "unknown":
        summary.append(f"Model: {model_name}")

    if persona_name and persona_name != "none":
        summary.append(f"Persona: {persona_name}")

    if total_tokens:
        summary.append(f"Tokens: {total_tokens:,}")

    if tags:
        summary.append(f"Tags: {', '.join(tags)}")

    return "\n".join(summary)


def create_conversation_stats_report(conversation_manager: ConversationManager) -> str:
    """
    Create a formatted report of conversation statistics.

    Args:
        conversation_manager: ConversationManager instance

    Returns:
        Formatted string report
    """
    stats = conversation_manager.get_statistics()

    lines = []
    lines.append("=== Conversation Statistics ===")
    lines.append(f"Total conversations: {stats.get('total_conversations', 0):,}")
    lines.append(f"Total messages: {stats.get('total_messages', 0):,}")
    lines.append(f"Total tokens: {stats.get('total_tokens', 0):,}")

    # Add role breakdown if available
    if "messages_by_role" in stats:
        lines.append("\nMessage breakdown by role:")
        for role, count in stats["messages_by_role"].items():
            lines.append(f"  - {role}: {count:,}")

    # Add model usage if available
    if "most_used_model" in stats:
        model_info = stats["most_used_model"]
        lines.append(
            f"\nMost used model: {model_info.get('model')} ({model_info.get('count')} times)"
        )

    # Add activity stats if available
    if "most_active_day" in stats:
        activity = stats["most_active_day"]
        lines.append(
            f"Most active day: {activity.get('date')} with {activity.get('message_count')} messages"
        )

    # Add token stats
    if "avg_tokens_per_message" in stats:
        lines.append(f"Average tokens per message: {stats.get('avg_tokens_per_message'):.1f}")

    return "\n".join(lines)
